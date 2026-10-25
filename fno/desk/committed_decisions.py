"""The books' committed decisions as the daily run sees them (story E3 with D3, judge 82). On time is what the collector
observes at the deadline: it pulls, and only runs visible in that commit count, whatever their committer clock says (a
run committed at 15:11:50 but pushed at 15:13 is late). The committer time before the deadline is the second check,
and D3's rule (committed before the execution snapshot started) the third, at the fill. The fills read only the runs
the decisions step recorded, by run ID and holding commit. Turning a run into entry orders is each book's part (E5, F5,
F6), behind `OrderBuilder`, done at the fill, never here (judge 84: a refusal there must not stop the day).

The day's decision is the **first** original run in the shared run order (story D3b, decisions 59 b and 61): a later
run, a second checkout's run or a correction committed before the deadline never replaces it. Every other run of the
day is listed for the run log, a correction with what it corrects and why, and is never collected."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Protocol

from ..playbook.decision_store import SUMS_FILE, DecisionStore
from ..playbook.run_order import OrderedRun, corrections, ordered_runs
from ..playbook.run_order import RunCommits as OrderCommits
from .daily_ports import CommittedDecision, DecisionSource
from .pack_items import available_time


class RunCommits(OrderCommits, Protocol):
    def observed(self) -> str: ...


class RunNotRecorded(ValueError):
    """The run the decisions step recorded is gone or held by another commit: it is never filled."""


class D3CommittedDecisions(DecisionSource):
    def __init__(self, root: Path, git: RunCommits):
        self.root, self.git = Path(root), git

    def observe(self) -> str:
        return self.git.observed()

    def committed(self, book: str, day: date, deadline: datetime) -> CommittedDecision | None:
        """The first committed original run, if it is on time (runs come in commit-time order, so a later one is
        never on time when the first is not)."""
        for run in self._ordered(book, day):
            if run.commit is None or corrections(run.path):
                continue
            if run.committed_at >= deadline:
                return None
            return CommittedDecision(book, run.run_id, run.commit, run.committed_at, run.path)
        return None

    def others(self, book: str, day: date, taken: str | None) -> list[dict]:
        rows = []
        for run in self._ordered(book, day):
            if run.run_id == taken:
                continue
            moment = run.committed_at.isoformat() if run.committed_at else None
            row = {"run_id": run.run_id, "commit": run.commit, "committed_at": moment}
            rows.append(row | ({"corrections": fixes} if (fixes := corrections(run.path)) else {}))
        return rows

    def recorded(self, book: str, day: date, run_id: str, commit: str) -> CommittedDecision:
        run = DecisionStore(self.root, book).day_folder(day) / run_id
        decision = self._decision(book, run) if run.is_dir() else None
        if decision is None or decision.commit != commit:
            raise RunNotRecorded(f"{book} {run_id}: not held by the recorded commit {commit}")
        return decision

    def _ordered(self, book: str, day: date) -> list[OrderedRun]:
        return ordered_runs(self.root, DecisionStore(self.root, book).runs(day), self.git)

    def _decision(self, book: str, run: Path) -> CommittedDecision | None:
        added = self.git.added_in((run / SUMS_FILE).relative_to(self.root).as_posix())
        moment = available_time(added[1]) if added else None
        if moment is None:
            return None
        return CommittedDecision(book, run.name, added[0], moment, run)
