"""The daily run's reviews after the exits (story O1, judge 214): E6's scorecards with their automatic pauses (the
catastrophic and cumulative-loss rules) run every session, marked at the day's execution snapshot, and their status
changes are committed. LR3's drift monitor joins as a second `Review` in the same step. Without a valid snapshot an
open position cannot be marked, so a catastrophic loss on it cannot be judged: when some book holds one, the step is
refused and the next session opens nothing new (`DailyRun._unscored`); with none open there is nothing to mark and
the step is ok (judge 178 addendum 13). Paper and research only: a pause never places an order."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from ..constants import STEP_OK, STEP_REFUSED
from ..desk.daily_ports import DayStep
from ..desk.daily_steps import StepOutcome
from ..desk.run_log import RunLog
from ..desk.snapshot import ExecutionSnapshotSource
from ..scorecard.run import ScorecardRun
from ..scorecard.scorecard import snapshot_marks

SNAPSHOT_STEP = "snapshot"
UNMARKED = (
    "no valid execution snapshot today: {open} open positions cannot be marked, so their loss rules were not judged"
)
NOTHING_TO_MARK = "no valid execution snapshot today, and no open position to mark"


@dataclass(frozen=True)
class ReviewResult:
    lines: list[str]  # one per finding or action (a pause, an alert)
    open_positions: int = 0  # the open positions it judged at the marks (a review of none reports 0)


class Review(ABC):
    @abstractmethod
    def review(self, day: date, marks: Mapping) -> ReviewResult:
        """Judges the day at these marks."""


class ScorecardReview(Review):
    def __init__(self, run: ScorecardRun):
        self.run = run

    def review(self, day: date, marks: Mapping) -> ReviewResult:
        cards, actions = self.run.run(day, marks, pause=True)
        return ReviewResult([f"{len(cards)} scorecards", *actions], sum(len(card.open_marks) for card in cards))


class ReviewsStep(DayStep):
    def __init__(self, reviews: Sequence[Review], snapshots: ExecutionSnapshotSource, root: Path,
                 changed: Callable[[Sequence[str]], list], pathspecs: Sequence[str]):  # fmt: skip
        self.reviews, self.snapshots, self.root, self.changed, self.pathspecs = (
            reviews, snapshots, Path(root), changed, pathspecs)  # fmt: skip

    def run(self, day: date) -> StepOutcome:
        log = RunLog.open(self.root, day)
        snapshot = log.result(SNAPSHOT_STEP) if log.done(SNAPSHOT_STEP) else {}
        valid = bool(snapshot.get("valid"))
        marks = snapshot_marks(self.snapshots.snapshot(day, snapshot["snapshot_id"])) if valid else {}
        results = [review.review(day, marks) for review in self.reviews]
        lines, open_positions = [line for r in results for line in r.lines], sum(r.open_positions for r in results)
        if valid or not open_positions:
            status, reason = STEP_OK, "; ".join(lines) + ("" if valid else f"; {NOTHING_TO_MARK}")
        else:
            status, reason = STEP_REFUSED, UNMARKED.format(open=open_positions)
        result = {"status": status, "reason": reason, "lines": lines, "marked_contracts": len(marks),
                  "open_positions": open_positions}  # fmt: skip
        return StepOutcome({"snapshot_id": snapshot.get("snapshot_id")}, result, tuple(self.changed(self.pathspecs)))
