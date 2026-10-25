"""The committed decision runs the desk used, read from E3's daily run logs (`journal/runs/<day>.json`) and D3's
stores (story S2). A run counts only when the day's log names it (run ID and holding commit): a run decided but not
collected by the deadline was never the book's decision. It is on time when it was committed before the day's
execution snapshot started (E3's late rule)."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from ..constants import JOURNAL_FOLDER, RUN_LOG_DECISIONS_STEP, RUN_LOG_EXITS_STEP
from ..desk.run_log import RUNS_FOLDER, book_results
from ..playbook.decision_store import INPUTS_FILE, DecisionStore
from ..playbook.opportunities import SHADOW

DECISIONS_STEP, SNAPSHOT_STEP, EXITS_STEP = RUN_LOG_DECISIONS_STEP, "snapshot", RUN_LOG_EXITS_STEP
NO_EXITS_STEP, NOT_REVIEWED = "no exit review ran", "exit review not recorded as done"
NOT_CHECKED, REVIEW_FAILED = "not checked against prices: {reason}", "exit review failed: {error}"


@dataclass(frozen=True)
class DayRun:
    book: str
    day: date
    run_id: str
    commit: str
    on_time: bool


class CommittedRuns:
    def __init__(self, root: Path):
        self.root = Path(root)

    def logs(self) -> Iterator[tuple[date, dict]]:
        folder = self.root / JOURNAL_FOLDER / RUNS_FOLDER
        for path in sorted(folder.glob("*.json")) if folder.is_dir() else ():
            yield date.fromisoformat(path.stem), json.loads(path.read_text(encoding="utf-8"))["steps"]

    def runs(self) -> list[DayRun]:
        found = []
        for day, steps in self.logs():
            snapshot = steps.get(SNAPSHOT_STEP)
            started = datetime.fromisoformat(snapshot["started_at"]) if snapshot else None
            for book, entry in sorted(_decided(steps).items()):
                if "run_id" in entry:
                    late = started is None or datetime.fromisoformat(entry["committed_at"]) >= started
                    found.append(DayRun(book, day, entry["run_id"], entry["commit"], not late))
        return found

    def uncollected(self, books: Sequence[str]) -> dict[str, list[dict]]:
        """Each book's runs the decisions step saw but did not collect (story D3b), with corrections: shown apart on
        the board, never scored."""
        found: dict[str, list[dict]] = {book: [] for book in books}
        for day, steps in self.logs():
            for book, entry in sorted(_decided(steps).items()):
                found.setdefault(book, []).extend({"day": day.isoformat(), **o} for o in entry.get("others", ()))
        return found

    def snapshot_ids(self) -> dict[date, str]:
        """Each day's valid execution snapshot, the one the day's fills and marks used."""
        ids = {}
        for day, steps in self.logs():
            result = steps.get(SNAPSHOT_STEP, {}).get("result", {})
            if result.get("valid"):
                ids[day] = result["snapshot_id"]
        return ids

    def records(self, run: DayRun) -> list[dict]:
        """The book's own records of a run. D2's shadow records share the run's folder but are never the book's
        action: kept out here, so no reader keyed by opportunity ID can take a shadow's for the book's (R3 probe)."""
        folder = DecisionStore(self.root, run.book).day_folder(run.day) / run.run_id
        paths = sorted(p for p in folder.glob("*.json") if p.name != INPUTS_FILE)
        found = [json.loads(p.read_text(encoding="utf-8")) for p in paths]
        return [r for r in found if r.get("mode") != SHADOW]

    def missed_runs(self, book: str, sessions: Sequence[date], held: Callable[[date], bool]) -> list[dict]:
        """Scoreboard B's missed runs (story S6 section 5), read from the run logs: a session with no run of the book
        collected is `missed_decision`; one with no exit review while a trade was held at the previous session's close
        is `missed_exit_review`, as is an exits step where the book's review failed (`error`) or its exits were held up
        (`waiting`), the daily run's own rule (daily_run.py). Closed days are never listed, since `sessions` holds
        sessions only."""
        logs, found = dict(self.logs()), []
        for i, day in enumerate(sessions):
            if i == len(sessions) - 1 and day not in logs:
                continue  # the report day before its run: not run yet, not missed
            steps = logs.get(day, {})
            collected = "run_id" in _decided(steps).get(book, {})
            why = _unreviewed(steps, book) if i > 0 and held(sessions[i - 1]) else ""
            if not collected or why:
                found.append({"day": day.isoformat(), "missed_decision": not collected,
                              "missed_exit_review": bool(why), "exit_review": why})  # fmt: skip
        return found


def _decided(steps: dict) -> dict:
    """The decisions step's books; none when the step itself failed or was refused (DRY2 R2): every book is then
    uncollected, never a crash on the failure's own fields."""
    return book_results(steps.get(DECISIONS_STEP, {}).get("result", {}))


def _unreviewed(steps: dict, book: str) -> str:
    """Why the book's exits were not reviewed that day, or "" when they were. E3 writes `reviewed` on every outcome:
    `waiting` means no valid snapshot, so the held trades were not checked against prices (orchestrator, 16 Oct)."""
    if EXITS_STEP not in steps:
        return NO_EXITS_STEP
    outcome = book_results(steps[EXITS_STEP].get("result", {})).get(book, {})
    if outcome.get("reviewed") is True:
        return ""
    if "waiting" in outcome:
        return NOT_CHECKED.format(reason=outcome.get("reason") or "no valid snapshot")
    return REVIEW_FAILED.format(error=outcome["error"]) if outcome.get("error") else NOT_REVIEWED
