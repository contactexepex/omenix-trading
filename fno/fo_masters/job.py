"""One run of A20a's job: every day the ban list (filed under the trade date it names: the run day's session or the
next one), and on a trading day today's market lots and the check that today's ban list is archived, go to Drive with
their manifest rows. Each step prints one line; any failed step makes one #fno-desk alert naming every failure, and
the run exits 1."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date

from ..alerts.sender import AlertSender
from ..research_data.calendar import SessionCalendar
from ..storage.manifest_commit import ManifestRecorder
from ..storage.snapshot_taker import NOT_SERVED
from ..storage.trading_days import is_trading_day

NOT_A_TRADING_DAY = "{day}: not a trading day; only the ban list for the next session is taken"
NO_LIST_TODAY = (
    "no ban list archived for today's session {day} (NSE wrote none, or every run before its replacement failed)"
)
STEP_OK, STEP_FAILED = "{name}: ok: {line}", "{name}: failed: {reason}"
NOT_COMMITTED_MARK = " NOT committed"
ALERT = "Omenix F&O master files for {day}: NOT complete: {failures}. Run log: {where}"
NOT_SERVED_SUFFIX = NOT_SERVED.removeprefix("{path}")  # a taker's line for a 404: today's copy is missing


@dataclass(frozen=True)
class Step:
    name: str
    run: Callable[[date], str]  # one line on success; raises on a failure
    every_day: bool = False  # False: trading days only


class StepFailed(RuntimeError):
    """A step's own verdict that it did not finish (e.g. NSE did not serve today's file)."""


def taken(line: str) -> str:
    """A taker's line, or StepFailed when NSE did not serve the file (a missing daily rule is a failure, not news)."""
    if line.endswith(NOT_SERVED_SUFFIX):
        raise StepFailed(line)
    return line


def ban_list_step(take: Callable[[date], str], archived: Callable[[date], bool],
                  is_trading_day: Callable[[date], bool]) -> Callable[[date], str]:  # fmt: skip
    """Takes NSE's current ban list; on a trading day, fails unless that day's own list is archived by now (stale)."""

    def run(day: date) -> str:
        line = taken(take(day))
        if is_trading_day(day) and not archived(day):
            raise StepFailed(NO_LIST_TODAY.format(day=day))
        return line

    return run


class FoMastersJob:
    def __init__(self, calendar: SessionCalendar, steps: Sequence[Step], recorder: ManifestRecorder,
                 alerts: AlertSender, where: str, out=print):  # fmt: skip
        self.calendar, self.steps, self.recorder = calendar, steps, recorder
        self.alerts, self.where, self.out = alerts, where, out

    def run(self, day: date) -> int:
        """0 when every step of the day succeeded; 1 (after one alert) otherwise."""
        trading = is_trading_day(self.calendar, day)
        if not trading:
            self.out(NOT_A_TRADING_DAY.format(day=day))
        steps = [step for step in self.steps if trading or step.every_day]
        failures = [failure for step in steps if (failure := self._run(step, day))]
        committed = self.recorder.commit(f"fo-masters {day}")
        self.out(committed)
        if NOT_COMMITTED_MARK in committed:
            failures.append(committed)
        if not failures:
            return 0
        self.out(self.alerts.send(ALERT.format(day=day, failures="; ".join(failures), where=self.where)))
        return 1

    def _run(self, step: Step, day: date) -> str | None:
        try:
            self.out(STEP_OK.format(name=step.name, line=step.run(day)))
            return None
        except (OSError, ValueError, RuntimeError) as exc:  # NSE, Drive (requests errors are OSError), a check, stale
            line = STEP_FAILED.format(name=step.name, reason=exc)
            self.out(line)
            return line
