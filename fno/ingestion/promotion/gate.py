"""The promotion gate (docs/PIPELINE_DESIGN.md): the only code that writes the Record from staged files. For one
archive path it keeps today's first-copy-wins rule: the EARLIEST-fetched staged copy that passes every check becomes the
record (the Record is write-once), and every later passing copy with other bytes is offered to the revision sink (the
existing A11 revisions area), so no version NSE published is lost. Failing copies stay in Staging with their reasons.
A record is never overwritten."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum

from fno.ingestion.promotion.checks import Candidate, PromotionCheck
from fno.ingestion.promotion.staging import StagedCopy, StagingArea
from fno.ingestion.storage.raw_store import RawFileStore


class Verdict(Enum):
    PROMOTED = "promoted"  # this call wrote the record
    ALREADY_RECORDED = "already recorded"  # the Record held the path before this call
    NOT_STAGED = "not staged"
    REJECTED = "rejected"  # nothing recorded, and every staged copy failed a check; left in Staging


class RevisionSink(ABC):
    @abstractmethod
    def capture(self, path: str, data: bytes, found_at: datetime) -> bool:
        """Keeps a later version of a recorded path (the A11 revisions area); True when it was new."""


@dataclass(frozen=True)
class Promotion:
    path: str
    verdict: Verdict
    reasons: tuple[str, ...] = ()  # why nothing was recorded (REJECTED)
    notes: tuple[str, ...] = ()  # copies that failed a check although the Record holds the path: log only
    revisions: int = 0  # later versions newly kept in the revisions area


class PromotionGate:
    def __init__(self, staging: StagingArea, record: RawFileStore, source: str, checks: Sequence[PromotionCheck],
                 revisions: RevisionSink):  # fmt: skip
        """`source`: the source tag whose staged copies are promoted (the authoritative one for this dataset);
        `record`: the write-once Record, written by nothing else; `revisions`: where later versions go."""
        self.staging, self.record, self.source = staging, record, source
        self.checks, self.revisions = tuple(checks), revisions

    def promote(self, path: str, day: date, filename: str) -> Promotion:
        copies = self.staging.copies(self.source, path)
        if not copies:
            return Promotion(path, Verdict.NOT_STAGED)
        passing, failures = self._sort(copies, day, filename)
        held = self.record.get(path)
        verdict = Verdict.ALREADY_RECORDED
        if held is None:
            if not passing:
                return Promotion(path, Verdict.REJECTED, tuple(failures))
            held, verdict = passing[0].data, Verdict.PROMOTED
            self.record.put(path, held)
        later = [copy for copy in passing if copy.data != held]
        kept = sum(self.revisions.capture(path, copy.data, copy.fetched_at) for copy in later)
        return Promotion(path, verdict, notes=tuple(failures), revisions=kept)

    def _sort(self, copies: list[StagedCopy], day: date, filename: str) -> tuple[list[StagedCopy], list[str]]:
        passing, failures = [], []
        for copy in copies:
            problems = [reason for check in self.checks if (reason := check.problem(Candidate(copy, day, filename)))]
            if problems:
                failures += problems
            else:
                passing.append(copy)
        return passing, failures
