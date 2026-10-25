"""Story O1's own steps around the desk's: one existing command each (weather, v4 forecasts, card), its files
committed by the daily run, plus the two rules every O1 step keeps: not before its `live_from` date, and a failure is
recorded with its reason and alerted once, never stopping the next step (design 9)."""

from __future__ import annotations

import time as clock_time
from collections.abc import Callable, Sequence
from datetime import date, datetime, time

from ..alerts.sender import AlertSender
from ..constants import STEP_FAILED, STEP_NOT_LIVE, STEP_OK, STEP_REFUSED
from ..desk.daily_ports import DayStep, Waiter
from ..desk.daily_steps import StepOutcome
from ..desk.git_limit import GitLocks
from ..models import IST
from .processes import Process, Processes

NOTHING_WRITTEN = "nothing written:"  # how `weather capture` and `forecast-v4 capture` print a refusal (exit 0)
NOT_LIVE = "not live before {live_from} (config.yaml daily.live_from)"
NO_DATE = "no live date set (config.yaml daily.live_from)"
FAILED_ALERT = "F&O daily run {day}: step {name} {status}: {reason}; the run goes on{note}"
POLL_SECONDS = 1.0
COMMAND_LIMIT_SECONDS = (
    600.0  # a hung command (a Groww call that never answers) is stopped, never holds the day forever
)
STOPPED_AT_LIMIT = "stopped after {minutes} minutes without ending; nothing of it committed{removed}"
STARTS_TOO_LATE = "not started: {now:%H:%M:%S} IST is after its last start, {by:%H:%M} IST on {day}"
LOCKS_REMOVED = "; the git lock files it left removed: {names}"


def wait(process: Process, sleep: Callable[[float], None] = clock_time.sleep, limit: float | None = None) -> int | None:
    """The command's exit code; None when it ran past `limit` seconds and was stopped."""
    code, waited = process.poll(), 0.0
    while code is None:
        if limit is not None and waited >= limit:
            process.stop()
            return None
        sleep(POLL_SECONDS)
        waited += POLL_SECONDS
        code = process.poll()
    return code


def outcome(arguments: Sequence[str], code: int, lines: list[str], paths=(), errors: Sequence[str] = ()) -> StepOutcome:
    """A command's exit code and printed lines as a step's status: 0 is ok, or refused when it printed that it wrote
    nothing (a cutoff passed, stale closes); anything else failed. The reason is its last line."""
    refused = code == 0 and any(NOTHING_WRITTEN in line for line in lines)
    status = STEP_REFUSED if refused else STEP_OK if code == 0 else STEP_FAILED
    reason = lines[-1] if lines else f"exit code {code}, nothing printed"
    result = {"status": status, "reason": reason, "exit_code": code, "lines": lines}
    if errors:
        result["stderr"] = list(errors)  # the private full log only, never the committed one (O1-status-only)
    return StepOutcome({"command": list(arguments)}, result, tuple(paths))


class CommandStep(DayStep):
    """Runs one command for the day and commits the files it changed under its pathspecs (none: it commits its own
    files, as Book 1's decision does). A command still running after `COMMAND_LIMIT_SECONDS` is stopped and failed
    (judge 178 add. 1 note 6: a hang never delays the 3 pm capture, which starts before any command). It does not
    protect the 15:12 deadline for `book1`, which can start as late as about 15:10; E3's late rule decides then."""

    def __init__(
        self,
        processes: Processes,
        arguments: Callable[[date], Sequence[str]],
        pathspecs: Sequence[str],
        changed: Callable[[Sequence[str]], list],
        sleep: Callable[[float], None] = clock_time.sleep,
        locks: GitLocks | None = None,
    ):
        self.processes, self.arguments, self.pathspecs, self.changed, self.sleep, self.locks = (
            processes,
            arguments,
            pathspecs,
            changed,
            sleep,
            locks,
        )

    def run(self, day: date) -> StepOutcome:
        """A command stopped at its limit may have been inside a git commit (Book 1's `desk book1` commits its own
        decision): the git locks it left are removed by story O2's rule, so the next commit works."""
        arguments = self.arguments(day)
        before = self.locks.present() if self.locks else set()
        process = self.processes.start(arguments)
        code = wait(process, self.sleep, COMMAND_LIMIT_SECONDS)
        if code is None:
            removed = self.locks.remove_new(before) if self.locks else []
            names = LOCKS_REMOVED.format(names=", ".join(removed)) if removed else ""
            reason = STOPPED_AT_LIMIT.format(minutes=int(COMMAND_LIMIT_SECONDS // 60), removed=names)
            return StepOutcome({"command": list(arguments)}, {"status": STEP_FAILED, "reason": reason})
        paths = self.changed(self.pathspecs) if self.pathspecs else ()
        return outcome(arguments, code, process.lines(), paths, process.errors())


class LiveFrom(DayStep):
    """Does nothing before its live date (none set: never), so no live record starts before the owner or a freeze
    decides (a first live weather record ends M1's back-fill)."""

    def __init__(self, step: DayStep, live_from: date | None):
        self.step, self.live_from = step, live_from

    def run(self, day: date) -> StepOutcome:
        if self.live_from is None or day < self.live_from:
            why = NO_DATE if self.live_from is None else NOT_LIVE.format(live_from=self.live_from)
            return StepOutcome({"live_from": str(self.live_from)}, {"status": STEP_NOT_LIVE, "reason": why})
        return self.step.run(day)


class Alerted(DayStep):
    """A step that failed, was refused or raised is recorded with its reason and alerted once; the run goes on."""

    def __init__(self, name: str, step: DayStep, alerts: AlertSender, status_alerts: bool = True, note: str = ""):
        """`status_alerts=False`: only a raise is alerted (the quote parts' results, whose commands alert for
        themselves, A4c). `note` ends the alert (MS-P1j2: why a rerun will not retry the school)."""
        self.name, self.step, self.alerts, self.status_alerts, self.note = name, step, alerts, status_alerts, note

    def run(self, day: date) -> StepOutcome:
        try:
            done, raised = self.step.run(day), False
        except Exception as failure:  # noqa: BLE001 - one O1 step's failure must never stop the desk (design 9)
            done, raised = (
                StepOutcome({}, {"status": STEP_FAILED, "reason": f"{type(failure).__name__}: {failure}"}),
                True,
            )
        status = done.result.get("status")
        if status in (STEP_FAILED, STEP_REFUSED) and (raised or self.status_alerts):
            reason = done.result["reason"]
            self.alerts.send(FAILED_ALERT.format(day=day, name=self.name, status=status, reason=reason, note=self.note))
        return done


class NotBefore(DayStep):
    """Starts its step no earlier than `at` IST on the run's day, waiting through the run's waiter (so a quote part
    still running is serviced); a run already past `at` starts it at once."""

    def __init__(self, step: DayStep, at: time, waiter: Waiter):
        self.step, self.at, self.waiter = step, at, waiter

    def run(self, day: date) -> StepOutcome:
        self.waiter.until(datetime.combine(day, self.at, IST))
        return self.step.run(day)


class StartsBy(DayStep):
    """Refuses to start its step after `by` IST on the run's day (MS-P1j2: a school run that starts late seals a
    session whose fills law 6 then refuses; a rerun or a past day's run is late the same way). Ending is not checked."""

    def __init__(self, step: DayStep, by: time, clock: Callable[[], datetime]):
        self.step, self.by, self.clock = step, by, clock

    def run(self, day: date) -> StepOutcome:
        now, last = self.clock(), datetime.combine(day, self.by, IST)
        if now > last:
            why = STARTS_TOO_LATE.format(now=now.astimezone(IST), by=self.by, day=day)
            return StepOutcome({"starts_by": last.isoformat()}, {"status": STEP_REFUSED, "reason": why})
        return self.step.run(day)
