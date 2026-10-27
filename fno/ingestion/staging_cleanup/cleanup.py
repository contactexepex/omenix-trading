"""The staging cleanup (story S1): staged copies older than a cutoff that are PROVEN promoted are moved to Drive's
trash, oldest first, at most `limit` copies examined per run. Without a deleter it only reports what it would do (the
default).

Order of every decision, cheapest first: age (from the copy's own fetch stamp, no read), then the proof (reads the copy
and the Record), then the removal. A copy that is young, unproven, unreadable or whose source has no proof is kept; a
removal that fails is counted and the copy stays. Counts only: the report never holds a path."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from fno.ingestion.promotion.staging import StagingArea
from fno.ingestion.staging_cleanup.proof import PromotedProof
from fno.ingestion.staging_cleanup.trash import StagingTrash
from fno.shared.models import now_utc

MAX_AGE = timedelta(days=7)
DEFAULT_LIMIT = 500
# the report's fixed keys
SCANNED, YOUNG, UNPROVEN, NO_RULE, UNREADABLE = "scanned", "young", "unproven", "no_rule", "unreadable"
WOULD_TRASH, TRASHED, ALREADY_GONE, FAILED, LIMIT_REACHED = (
    "would_trash",
    "trashed",
    "already_gone",
    "failed",
    "limit_reached",
)
KEYS = (SCANNED, YOUNG, UNPROVEN, NO_RULE, UNREADABLE, WOULD_TRASH, TRASHED, ALREADY_GONE, FAILED, LIMIT_REACHED)


@dataclass
class CleanupReport:
    counts: Counter = field(default_factory=Counter)
    apply: bool = False

    @property
    def ok(self) -> bool:
        return not (self.counts[FAILED] or self.counts[UNREADABLE])

    def line(self) -> str:
        mode = "applied" if self.apply else "report only"
        return f"staging cleanup ({mode}): " + ", ".join(f"{key} {self.counts[key]}" for key in KEYS)


class StagingCleanup:
    def __init__(self, staging: StagingArea, proofs: Mapping[str, PromotedProof], trash: StagingTrash | None,
                 clock: Callable[[], datetime] = now_utc, max_age: timedelta = MAX_AGE,
                 limit: int = DEFAULT_LIMIT):  # fmt: skip
        """`proofs`: source tag -> its proof (a tag without one is kept whole); `trash`: None for report only."""
        self.staging, self.proofs, self.trash = staging, dict(proofs), trash
        self.clock, self.max_age, self.limit = clock, max_age, limit

    def run(self, sources: list[str]) -> CleanupReport:
        report = CleanupReport(apply=self.trash is not None)
        examined = 0
        for source in sources:
            for path in self.staging.archive_paths(source):
                for fetched_at, stamp in self.staging.stamps(source, path):
                    if self.clock() - fetched_at <= self.max_age:  # strictly older than the cutoff, by its own stamp
                        report.counts[YOUNG] += 1
                        continue
                    if examined >= self.limit:
                        report.counts[LIMIT_REACHED] = 1
                        return report
                    examined += 1
                    self._one(source, path, stamp, report)
        return report

    def _one(self, source: str, path: str, stamp: str, report: CleanupReport) -> None:
        report.counts[SCANNED] += 1
        proof = self.proofs.get(source)
        if proof is None:
            report.counts[NO_RULE] += 1
            return
        try:
            copy = self.staging.read(source, path, stamp)
        except Exception:  # noqa: BLE001 - Drive errors may name paths; only the count is kept
            copy = None
        if copy is None:
            report.counts[UNREADABLE] += 1
            return
        if not proof.promoted(copy):
            report.counts[UNPROVEN] += 1
            return
        if self.trash is None:
            report.counts[WOULD_TRASH] += 1
            return
        self._remove(source, path, stamp, report)

    def _remove(self, source: str, path: str, stamp: str, report: CleanupReport) -> None:
        try:
            gone = self.trash.trash(source, path, stamp)
        except Exception:  # noqa: BLE001 - the copy stays; only the count is kept
            report.counts[FAILED] += 1
            return
        report.counts[TRASHED if gone else ALREADY_GONE] += 1
