"""The paper desk's daily run (story E3, design 13.5 steps 4-5): `DailyRun.run(day)` walks the fixed timetable.

1. On a day that is not a recorded session (A7 calendar: closed, or a muhurat-only evening) nothing runs.
2. `versions`: Book 1's D6 version is kept current before any decision (judge 80).
3. `pack` (from about 14:58): E2's common pack, built only once the 3 pm canonical snapshot is committed (judge 72),
   retried until the recorder's window ends.
4. `decisions` (at the deadline): the collector pulls once; each book's run visible then is recorded (run ID, holding
   commit, the origin commit seen); a book without one gets a committed "no decision (late)" and cannot join later.
   A slow book delays nothing: decisions are read, not awaited. Collected after the deadline (a restart), every book is
   late (fail closed).
5. `snapshot` (at the execution time): one capture for every book, with one common retry if it is not valid.
6. `fills`: only the runs recorded at the deadline, each with a completed C4 pass, fill against that one snapshot;
   none if it is invalid.
7. `exits`: every book's exit review, whatever happened before (risk-reducing exits always run).
8. `trade_marks`: every account's open trades valued at the session's snapshot by S2's rule, with its equity row (story
   E2d), so a trade opened or kept today is valued today.

The steps run in the order of `DAILY_RUN_STEPS` (story O1, the one tuple the health check O8 reads): the desk's own
above, and around them O1's `DayStep`s (the margin check, weather, v4 forecasts and the quote parts before, Book 1's
decision after the pack, the parts' results and the card after), each run at once when its turn comes. A name with no
step given (E3's tests) is passed over.

Each step's start, end, inputs and result go to `journal/runs/<date>.json`, committed after the step; a restarted run
skips every step already recorded, so nothing is done twice. A commit that fails (a refused raw quote file, a failed
pull, a push rejected every time) or a git read that fails (`GitFailed`, e.g. the decisions' pull or a run's commit
read in the fills) stops the run at that step: one alert naming why, what is missed and the hand fix, no later step,
nothing more committed, and `RunStopped` for the command to end on one line (decision 44). The rerun
first commits that failed commit's files exactly as they were recorded, and never repeats the step that made them
(`PendingCommitter`, decision 47). Any other error in a step fails that step only (DRY2 R2, 24 Oct): logged with its
type and one line, alerted, and the run goes on; a step that reads a failed step's result (`NEEDS`) is refused. A
rerun on the same day runs such a failed step again when it is safe and useful to repeat (`RETRIED_ON_RERUN`, DRY2
SF1); the others stay failed for the day, and the alert says which. The fills are never retried and never start after
`fills_by` (owner, 24 Oct, DESK_DECISIONS "a failed fills step is never retried"): a rerun chosen after the price is
known must not decide whether a paper trade exists (judges 569.2 SF3 and 570.2 finding 1).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import date, datetime, time, timedelta
from pathlib import Path

from ..constants import (
    DAILY_RUN_STEPS,
    OWNER_TIMING_STEP,
    REVIEWS_STEP,
    RUN_LOG_DECISIONS_STEP,
    RUN_LOG_EXITS_STEP,
    RUN_LOG_TRADE_MARKS_STEP,
    STEP_FAILED,
    STEP_REFUSED,
)
from ..quotes.recorder import RECORDED_SESSION_KINDS
from ..research_data.calendar import SessionCalendar
from ..research_engine.ledger import GitFailed
from .daily_ports import RUN_STOPS, CommitFailed, DayStep, StepInterrupted, Waiter
from .daily_steps import DeskSteps, StepOutcome
from .pending_commit import PendingChanged, PendingCommitter
from .private_files import PrivateFiles
from .run_log import RETRY, RunLog, problem_steps
from .step_recorder import AsGiven, StepRecorder
from .trade_marking import MarkingStep

SKIPPED = "skipped"
STOPPED = "F&O paper desk {day}: run STOPPED at {where}, no later step runs{missed}: {what}: {reason}. {fix}"
COMMIT_FAILED = "the commit failed"
GIT_FAILED = "a git read failed"
EXITS_MISSED = "; exits not reviewed today"
RERUN = "Fix: remove the cause, then rerun `fno daily run` (it commits these files as recorded, never repeating a step)"
READ_RERUN = "Fix: remove the cause, then rerun `fno daily run` (it skips the steps already recorded)"
PUSHES = "; the rerun pushes the local commit"
RECOVERY = "the rerun's start"
DOWNLOAD = "the download of the private paper records"
PACK_RETRY = timedelta(seconds=30)
STEP_ERROR = ("F&O paper desk {day}: step {name} FAILED ({reason}){written}; the run goes on, the steps that need it "
              "are refused; {rerun}")  # fmt: skip
WRITTEN = " after {count} trades were recorded in their accounts; those records stay there, check them"
RERUN_RETRIES = "a rerun today retries it (nothing it wrote is done twice)"
RERUN_FINAL = "a rerun today will not retry it: {why}"
# DRY2 SF1 (orchestrator, 24 Oct 06:24): the desk steps a rerun on the same day runs again after an unexpected error,
# each idempotent by its event IDs, or replacing the day's own rows (O1's claims, "Round 2"); the rest stay failed for
# the day, with why. The fills are final (owner, 24 Oct: "1 - A"): risk-reducing exits and marks may come late, a new
# trade never does
RETRIED_ON_RERUN = ("exits", RUN_LOG_TRADE_MARKS_STEP)
NOT_RETRIED = {
    "fills": "failed fills are final for the day: no other new desk trade opens today (fail closed)",
    "versions": "a version registered after the day's decision cannot count for it (D6)",
    "pack": "the decisions and the snapshot's checks already ran without it",
    RUN_LOG_DECISIONS_STEP: "what was visible at the deadline cannot be observed later",
    "snapshot": "a second capture would split the day's one execution snapshot",
}
NOT_A_DESK_STEP = "only the desk's own steps are retried"
NEEDS_FAILED = "needs {needed}, which failed today"
NEEDS_MISSING = "needs {needed}, which has not run today"
NEEDS_REFUSED = "needs {needed}, which was refused today"
NEEDS_PROBLEM = {STEP_FAILED: NEEDS_FAILED, STEP_REFUSED: NEEDS_REFUSED}  # each status `problem_steps` names
# DRY2 R2 (24 Oct): the steps that read another step's logged result, and which; the rest read their own inputs (the
# exits and the marks check the snapshot through the gate themselves, so risk-reducing exits always run)
NEEDS = {"fills": ("snapshot", RUN_LOG_DECISIONS_STEP)}
# The owner's ruling (24 Oct) and decision 47's rerun: a run that did not take the day's snapshot (a rerun after a
# stop) starts no fills after `fills_by`, as a person chose that rerun after the price moved
FILLS_LATE = (
    "it is {now:%H:%M:%S}, past fills_by {by:%H:%M}, in a run that did not take the day's snapshot: no fills by this "
    "run (fail closed); trades recorded before the stop stay in their accounts, check them"
)
FILLS_REFUSED = "F&O paper desk {day}: step fills REFUSED: {reason}"
NO_LOG = "the run of {day} stopped before any step"
BEFORE_EXITS = "the run of {day} stopped before its exits"
NOT_REVIEWED = "the exits of {day} were not reviewed ({why})"
HELD_UP = "due exits held up: {exits}"
UNSCORED = "the scorecards and automatic pauses of {day} did not run ({reason})"
UNFILLED = "today's owner-timing fills {status} ({reason})"
# a stop at the exits or any later step leaves the day's exits reviewed (E2d's marking and O1's steps after them)
AFTER_EXITS = tuple(f"step {name}" for name in DAILY_RUN_STEPS[DAILY_RUN_STEPS.index(RUN_LOG_EXITS_STEP) :])


class RunStopped(Exception):
    """The run stopped at a failed commit or git read; the message is the alert sent."""


class DailyRun:
    def __init__(self, steps: DeskSteps, calendar: SessionCalendar, committer: PendingCommitter, waiter: Waiter,
                 clock: Callable[[], datetime], marking: MarkingStep, files: PrivateFiles | None = None,
                 day_steps: Mapping[str, DayStep] | None = None, recorder: StepRecorder | None = None):  # fmt: skip
        self.steps, self.calendar, self.committer, self.waiter, self.clock = steps, calendar, committer, waiter, clock
        self.marking = marking  # story E2d
        self.ran_here: set[str] = set()  # the steps this run itself recorded
        self.files = files  # story E2c: the private records in Drive, downloaded before any step reads them
        self.day_steps = dict(day_steps or {})  # story O1's steps around the desk's
        self.recorder = recorder or AsGiven()  # story O1-status-only: the committed log holds status only

    def run(self, day: date) -> RunLog:
        self.ran_here = set()
        self._guarded(day, RECOVERY, self.committer.recover)
        if self.files is not None:
            self._guarded(day, DOWNLOAD, self.files.download)
        log = RunLog.open(self.steps.root, day)
        kind = self.calendar.session_kind(day)
        if kind not in RECORDED_SESSION_KINDS:
            if not log.done(SKIPPED):
                self._step(log, SKIPPED, lambda: StepOutcome({"session": kind}, {"reason": "not a session day"}))
            return log
        plan = self._plan(day, log)
        for name in DAILY_RUN_STEPS:  # a failed step is retried on its own day only: a later session read its log
            if name in plan and not log.done(name) and (name not in log.steps or self.on_its_day(day)):
                moment, action = plan[name]
                if moment is not None:
                    self.waiter.until(self.steps.timetable.at(day, moment))
                self._step(log, name, action)
        return log

    def on_its_day(self, day: date) -> bool:
        """Whether this run is on `day` itself, the only day a failed step is retried."""
        return self.clock().date() == day

    def _plan(self, day: date, log: RunLog) -> dict[str, tuple[time | None, Callable[[], StepOutcome]]]:
        """Each step by name: when it may start (None: at once, in its turn) and what it does."""
        times, steps = self.steps.timetable, self.steps
        desk = {
            "versions": (times.pack, lambda: steps.keep_versions(day)),
            "pack": (times.pack, lambda: self._pack(day)),
            RUN_LOG_DECISIONS_STEP: (times.decision_deadline, lambda: steps.collect_decisions(day)),
            "snapshot": (times.execution_snapshot, lambda: steps.take_snapshot(day)),
            "fills": (times.execution_snapshot, lambda: steps.fill(day, log.result("snapshot")["valid"],
                                                                   log.result(RUN_LOG_DECISIONS_STEP),
                                                                   self._unreviewed(day) | self._unscored(day)
                                                                   | self._unfilled(log))),
            "exits": (times.execution_snapshot, lambda: steps.review_exits(day)),
            RUN_LOG_TRADE_MARKS_STEP: (times.execution_snapshot, lambda: self.marking.run(day)),  # story E2d
        }  # fmt: skip
        return desk | {name: (None, lambda step=step: step.run(day)) for name, step in self.day_steps.items()}

    def _unreviewed(self, day: date) -> dict[str, str]:
        """Each book whose exits the last session did not review, with why (review 105 point 3, judge 159, review
        115): today it opens nothing new. The routine starts in a fresh container, so the committed run log is the only
        place this can be seen.
        - No log while an earlier one exists: a stop before any step (the recovery or the download). Every book.
        - A log without its exits step: a stop before the exits. Every book.
        - An exits step where a book's review failed (`error`) or exits were due but held up (`waiting`): that book.
          A day without a snapshot and nothing due leaves no exit unreviewed, so it blocks nothing."""
        last = self.calendar.previous_session(day)
        log = RunLog.open(self.steps.root, last)
        if not log.steps:
            stopped = any(d < last for d in RunLog.days(self.steps.root))
            return dict.fromkeys(self.steps.books, NO_LOG.format(day=last)) if stopped else {}
        if SKIPPED in log.steps:
            return {}
        if "exits" not in log.steps:
            return dict.fromkeys(self.steps.books, BEFORE_EXITS.format(day=last))
        if _failed(log.result("exits")):  # the step itself failed (R2): no book's exits were reviewed
            why = log.result("exits").get("reason", "")
            return dict.fromkeys(self.steps.books, NOT_REVIEWED.format(day=last, why=why))
        unreviewed = {book: r.get("error") or HELD_UP.format(exits="; ".join(r["waiting"]))
                      for book, r in log.result("exits").items() if r.get("error") or r.get("waiting")}  # fmt: skip
        return {book: NOT_REVIEWED.format(day=last, why=why) for book, why in unreviewed.items()}

    def _unfilled(self, log: RunLog) -> dict[str, str]:
        """Story E8 rule 11: when today's owner-timing fills failed or were refused, C2 would see yesterday's positions
        without this morning's fills and understate open risk, so no book opens anything new today (exits still run)."""
        result = log.result(OWNER_TIMING_STEP) if log.done(OWNER_TIMING_STEP) else {}
        if result.get("status") not in (STEP_FAILED, STEP_REFUSED):
            return {}
        reason = result.get("reason", "")  # a status-only log holds the reason's code (O1-status-only)
        return dict.fromkeys(self.steps.books, UNFILLED.format(status=result["status"], reason=reason))

    def _unscored(self, day: date) -> dict[str, str]:
        """Story O1 (judge 214): when the last session reviewed its exits but its scorecards and automatic pauses (E6)
        failed or were refused, a catastrophic loss may be unpaused, so no book opens anything new today (exits run).
        Only once the run has the step (E3's own tests do not)."""
        if REVIEWS_STEP not in self.day_steps:
            return {}
        last = self.calendar.previous_session(day)
        steps = RunLog.open(self.steps.root, last).steps
        if RUN_LOG_EXITS_STEP not in steps:  # no run, a closed day or a stop before the exits: `_unreviewed`'s rule
            return {}
        result = steps.get(REVIEWS_STEP, {}).get("result", {"status": STEP_FAILED, "reason": "not run"})
        if result.get("status") not in (STEP_FAILED, STEP_REFUSED):
            return {}
        return dict.fromkeys(self.steps.books, UNSCORED.format(day=last, reason=result.get("reason", "")))

    def _pack(self, day: date) -> StepOutcome:
        """Retries while the canonical snapshot is not committed yet, until the recorder's window ends."""
        last = self.steps.timetable.at(day, self.steps.timetable.pack_wait_until)
        outcome = self.steps.build_pack(day)
        while not outcome.result["built"] and self.clock() + PACK_RETRY <= last:
            self.waiter.until(self.clock() + PACK_RETRY)
            outcome = self.steps.build_pack(day)
        return outcome

    def _step(self, log: RunLog, name: str, action: Callable[[], StepOutcome]) -> None:
        def step() -> None:
            started = self.clock()
            outcome = self._refused(log, name) or self._too_late(log.day, name) or self._run_step(log.day, name, action)
            self.recorder.record(log, name, started, self.clock(), outcome.inputs, outcome.result)
            self.ran_here.add(name)
            paths: tuple[Path, ...] = (log.path, *outcome.paths)
            self.committer.commit(paths, f"Desk run {log.day} step {name}")

        self._guarded(log.day, f"step {name}", step)

    def _refused(self, log: RunLog, name: str) -> StepOutcome | None:
        """A step whose input step has not run today, or failed or was refused (O1's one rule, `problem_steps`), is
        refused, never run on a missing input (fail closed); the reason names which."""
        needs = NEEDS.get(name, ())
        missing = [needed for needed in needs if needed not in log.steps]  # a failed step awaiting its retry ran
        problems = problem_steps({needed: log.steps[needed] for needed in needs if needed in log.steps})
        if not (missing or problems):
            return None
        reasons = [NEEDS_MISSING.format(needed=", ".join(missing))] if missing else []
        for status, template in NEEDS_PROBLEM.items():
            names = [needed for needed, problem in problems if problem == status]
            reasons += [template.format(needed=", ".join(names))] if names else []
        return StepOutcome({}, {"status": STEP_REFUSED, "reason": "; ".join(reasons)})

    def _too_late(self, day: date, name: str) -> StepOutcome | None:
        """A fills step of a run that did not take the day's snapshot itself starts by `fills_by`, or is refused with
        one alert: only a person's rerun gets there (a stop, decision 47), chosen after the price moved. The run that
        took the snapshot fills at its prices with no choice in between, even when its own commit ends past the limit.
        The limit is on the step's start: its account writes may end a little later, at the snapshot's prices."""
        by = self.steps.timetable.at(day, self.steps.timetable.fills_by)
        now = self.clock()
        if name != "fills" or "snapshot" in self.ran_here or now <= by:
            return None
        reason = FILLS_LATE.format(now=now, by=by)
        self.steps.alerts.send(FILLS_REFUSED.format(day=day, reason=reason))
        return StepOutcome({}, {"status": STEP_REFUSED, "reason": reason})

    def _run_step(self, day: date, name: str, action: Callable[[], StepOutcome]) -> StepOutcome:
        """An unexpected error in one step fails that step only (DRY2 R2): it is logged with its type and one line,
        alerted, and the run goes on; a failed commit or git read still stops the run (`_guarded`). It is marked
        `retry` when a same-day rerun runs it again (SF1)."""
        try:
            return action()
        except RUN_STOPS:
            raise
        except Exception as error:  # noqa: BLE001 - any other error: this step fails, the day goes on
            interrupted = isinstance(error, StepInterrupted)
            cause = error.__cause__ if interrupted and error.__cause__ else error
            reason = f"{type(cause).__name__}: {_one_line(cause)}"
            written = WRITTEN.format(count=error.written) if interrupted else ""
            retry = name in RETRIED_ON_RERUN
            rerun = RERUN_RETRIES if retry else RERUN_FINAL.format(why=NOT_RETRIED.get(name, NOT_A_DESK_STEP))
            self.steps.alerts.send(STEP_ERROR.format(day=day, name=name, reason=reason, written=written, rerun=rerun))
            return StepOutcome({}, {"status": STEP_FAILED, "reason": reason, RETRY: retry})

    def _guarded(self, day: date, where: str, action: Callable[[], object]) -> None:
        """The one place a failed commit or git read is handled: the rerun's recovery, a step's own commit and any
        inside it. A git read cannot be trusted to answer later steps either, so it stops the run the same way."""
        try:
            action()
        except CommitFailed as failed:
            fix = "" if isinstance(failed, PendingChanged) else RERUN + (PUSHES if failed.unpushed else "")
            self._stop(day, where, COMMIT_FAILED, failed, fix)
        except GitFailed as failed:
            self._stop(day, where, GIT_FAILED, failed, READ_RERUN)

    def _stop(self, day: date, where: str, what: str, failed: Exception, fix: str) -> None:
        missed = "" if where in AFTER_EXITS else EXITS_MISSED
        text = STOPPED.format(day=day, where=where, missed=missed, what=what, reason=failed, fix=fix).rstrip(" ")
        self.steps.alerts.send(text)
        raise RunStopped(text) from failed


def _failed(result: dict) -> bool:
    return result.get("status") == STEP_FAILED


def _one_line(error: Exception) -> str:
    return (str(error).strip().splitlines() or [""])[0][:300]
