"""The promotion gate (docs/PIPELINE_DESIGN.md): the only code that writes the Record from staged files. For one
archive path it takes the staged copies (newest fetch first), skips what the Record already holds, and promotes the
newest copy that passes every check. Garbage is left in Staging with its reasons; a record is never overwritten: a
passing copy that differs from the Record is reported as a revision for the revision path, not written."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from enum import Enum

from fno.ingestion.promotion.checks import Candidate, PromotionCheck
from fno.ingestion.promotion.staging import StagingArea
from fno.ingestion.storage.raw_store import RawFileStore


class Verdict(Enum):
    PROMOTED = "promoted"
    ALREADY_RECORDED = "already recorded"
    NOT_STAGED = "not staged"
    REJECTED = "rejected"  # every staged copy failed a check; left in Staging
    DIFFERS_FROM_RECORD = (
        "differs from record"  # passes, but the Record holds other bytes: a revision, never overwritten
    )


@dataclass(frozen=True)
class Promotion:
    path: str
    verdict: Verdict
    reasons: tuple[str, ...] = ()


class PromotionGate:
    def __init__(self, staging: StagingArea, record: RawFileStore, source: str, checks: Sequence[PromotionCheck]):
        """`source`: the source tag whose staged copies are promoted (the authoritative one for this dataset);
        `record`: the write-once Record, written by nothing else."""
        self.staging, self.record, self.source, self.checks = staging, record, source, tuple(checks)

    def promote(self, path: str, day: date, filename: str) -> Promotion:
        copies = self.staging.copies(self.source, path)
        if not copies:
            return Promotion(path, Verdict.NOT_STAGED)
        held = self.record.get(path)
        reasons: list[str] = []
        for copy in copies:
            if held == copy.data:
                return Promotion(path, Verdict.ALREADY_RECORDED)
            problems = self._problems(Candidate(copy, day, filename))
            if problems:
                reasons += problems
                continue
            if held is not None:
                return Promotion(path, Verdict.DIFFERS_FROM_RECORD)
            self.record.put(path, copy.data)
            return Promotion(path, Verdict.PROMOTED)
        return Promotion(path, Verdict.REJECTED, tuple(reasons))

    def _problems(self, candidate: Candidate) -> list[str]:
        return [reason for check in self.checks if (reason := check.problem(candidate))]
