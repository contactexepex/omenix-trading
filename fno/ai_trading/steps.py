"""Story F1t's two O1 steps. `ai_fire` (right after the pack, before Book 1) starts the remote observer and fires each
live AI book once; `ai_collect` (after Book 1, before E3's `decisions`) waits for the observer's last reading, then
judges, promotes and records each book. Neither alerts itself: each returns `ok` when every live book was fired or
promoted, else `refused` naming each book's status and reason, and O1's `Alerted` sends the step's one line. With no
live book, both record `not_live` and call nothing."""

from __future__ import annotations

import atexit
from collections.abc import Callable, Sequence
from datetime import date, datetime, timedelta
from pathlib import Path

from ..ai.fire_once import FIRED
from ..ai.observed_receipts import GRACE, ObservationFile
from ..ai.remote_observer import LS_REMOTE_SECONDS
from ..constants import STEP_FAILED, STEP_NOT_LIVE, STEP_OK, STEP_REFUSED
from ..daily.processes import Process, Processes
from ..desk.daily_ports import DayStep, Waiter
from ..desk.daily_steps import StepOutcome
from .collect import DecisionCollector
from .fire import DecisionFirer
from .outcome import PROMOTED
from .paths import fired_path, observations_path
from .timing import DecisionTiming

# The steps' reasons, each a template O1-status-only registers as a code (`fno/daily/reason_codes.py`), so the public
# run log shows the code and the alert the full line (criterion 17)
NO_LIVE_BOOK = "no AI book is live today (config.yaml daily.live_from.book2_hybrid, book3_ai)"
DONE = "every live AI book done"
NOT_FIRED = "AI books not fired: {lines}; no trade today for these"
NOT_PROMOTED = "AI books not promoted: {lines}; no trade today for these"
OBSERVER_LOST = "AI books not promoted, the remote observer failed ({ended}): {lines}; no trade today for these"
BUDGET_UNREAD = "AI books fired, but BG1's budget could not be read (fired on purpose: cost only): {note}"
REHEARSAL_NO_FIRE = "rehearsal: AI decision routines are never fired; {books} not decided"
CONFIG_WRONG = "AI books not run: {reason}"
POLL = timedelta(seconds=1)
LiveBooks = Callable[[date], Sequence[str]]
Rehearsing = Callable[[], bool]  # REH1: true inside a rehearsal, which never fires a routine (criterion 18)


def _result(problems: dict[str, str], template: str, **fields: str) -> dict:
    if not problems:
        return {"status": STEP_OK, "reason": DONE}
    lines = "; ".join(f"{book} {why}" for book, why in sorted(problems.items()))
    return {"status": STEP_REFUSED, "reason": template.format(lines=lines, **fields), "n": len(problems)}


def _rehearsed(books: Sequence[str]) -> StepOutcome:
    reason = REHEARSAL_NO_FIRE.format(books=", ".join(books))
    return StepOutcome({"books": list(books)}, {"status": STEP_REFUSED, "reason": reason, "n": len(books)})


class ConfigRefused(DayStep):
    """Stands in for both steps when the AI books' settings are wrong (a misspelled `daily.live_from` key, a timetable
    out of order): the step fails with the reason, alerted once, and the rest of the day runs."""

    def __init__(self, reason: str):
        self.reason = reason

    def run(self, day: date) -> StepOutcome:
        return StepOutcome({}, {"status": STEP_FAILED, "reason": CONFIG_WRONG.format(reason=self.reason)})


class NotLive(DayStep):
    """Both steps on a day with no AI book live: `not_live`, and nothing built from the AI settings is read."""

    def run(self, day: date) -> StepOutcome:
        return _not_live()


class ObserverHandle:
    """The remote observer child, shared by the two steps (O1 builder, 16 Oct: never left running after the run).
    `ai_collect` reports how it ended and stops it; an exit hook stops it if the run ends before `ai_collect`."""

    def __init__(self):
        self.process: Process | None = None

    def start(self, processes: Processes, arguments) -> None:
        self.process = processes.start(arguments)
        atexit.register(self.stop)

    def report(self) -> str:
        """'' when it ended well or was never started (a rerun); else how it ended, for the step's reason."""
        if self.process is None:
            return ""
        code = self.process.poll()
        if code is None:
            return "the remote observer was still running (stopped now)"
        if code != 0:
            lines = self.process.lines()
            return f"the remote observer ended with exit code {code}" + (f" ({lines[-1]})" if lines else "")
        return ""

    def stop(self) -> None:
        if self.process is not None and self.process.poll() is None:
            self.process.stop()


def _not_live() -> StepOutcome:
    return StepOutcome({}, {"status": STEP_NOT_LIVE, "reason": NO_LIVE_BOOK})


class AiFireStep(DayStep):
    def __init__(self, root: Path, firer: DecisionFirer, timing: DecisionTiming, live: LiveBooks,
                 processes: Processes, observer: ObserverHandle, rehearsing: Rehearsing = lambda: False):  # fmt: skip
        self.root, self.firer, self.timing, self.live, self.processes = Path(root), firer, timing, live, processes
        self.observer, self.rehearsing = observer, rehearsing

    def run(self, day: date) -> StepOutcome:
        books = tuple(self.live(day))
        if not books:
            return _not_live()
        if self.rehearsing():
            return _rehearsed(books)
        self._start_observer(day)
        log = self.firer.fire(day, books, self.timing.fire_timing(day))
        problems = {b: f"{e.get('state')}: {e.get('reason', '')}" for b, e in log.items() if e.get("state") != FIRED}
        result = _result(problems, NOT_FIRED)
        note = self.firer.budget_note
        if note and result["status"] == STEP_OK:
            result = {"status": STEP_REFUSED, "reason": BUDGET_UNREAD.format(note=note)}
        return StepOutcome({"books": list(books)}, result, (self.root / fired_path(day),))

    def _start_observer(self, day: date) -> None:
        """Once a day: a rerun with readings already written starts none (a late reading would prove nothing)."""
        out = self.root / observations_path(day)
        if ObservationFile(out).read():
            return
        deadlines = self.timing.deadlines(day)
        arguments = ("ai", "observe-remote", "--out", str(out), "--deadline", deadlines.receipt.isoformat(),
                     "--deadline", deadlines.reveal.isoformat())  # fmt: skip
        self.observer.start(self.processes, arguments)


class AiCollectStep(DayStep):
    def __init__(self, root: Path, collector: DecisionCollector, timing: DecisionTiming, live: LiveBooks,
                 waiter: Waiter, clock: Callable[[], datetime], observer: ObserverHandle,
                 rehearsing: Rehearsing = lambda: False):  # fmt: skip
        self.root, self.collector, self.timing, self.live = Path(root), collector, timing, live
        self.waiter, self.clock, self.observer, self.rehearsing = waiter, clock, observer, rehearsing

    def run(self, day: date) -> StepOutcome:
        books = tuple(self.live(day))
        if not books:
            return _not_live()
        if self.rehearsing():
            return _rehearsed(books)
        deadlines = self.timing.deadlines(day)
        self._await_last_reading(day, deadlines.reveal)
        ended = self.observer.report()
        self.observer.stop()
        collected = self.collector.collect(day, books, deadlines, self.timing.late_at(day))
        problems = {
            b: f"{r['status']}: {r['reason']}" for b, r in collected.outcomes.items() if r["status"] != PROMOTED
        }
        statuses = {book: record["status"] for book, record in collected.outcomes.items()}
        labels = {book: r["strategy_label"].replace(" ", "_") for book, r in collected.outcomes.items()
                  if r.get("strategy_label")}  # fmt: skip  # the owner's label, as words the public log keeps
        result = _result(problems, OBSERVER_LOST, ended=ended) if ended else _result(problems, NOT_PROMOTED)
        inputs = {"books": list(books), "statuses": statuses, "strategy_labels": labels}
        return StepOutcome(inputs, result, collected.paths)

    def _await_last_reading(self, day: date, deadline: datetime) -> None:
        """Until the observer wrote its reading for the reveal deadline, or it can no longer be valid."""
        observations = ObservationFile(self.root / observations_path(day))
        give_up = deadline + GRACE + timedelta(seconds=LS_REMOTE_SECONDS)
        while not any(o.deadline == deadline for o in observations.read()) and self.clock() < give_up:
            self.waiter.until(min(self.clock() + POLL, give_up))
