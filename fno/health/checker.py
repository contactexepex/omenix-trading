"""One health run (story O8): every expectation over every session of the window, at one run time, plus the days the
health check itself did not run. A check that cannot tell (an unreadable file, an unknown push time) is `unknown`, never
`ok`. A malformed file (a value of the wrong type or shape) is that check's `unknown` too, so it never hides the
other checks; anything else that breaks stops the run, so the caller posts "health check FAILED"."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from ..constants import HEALTH_NOT_EXPECTED, HEALTH_UNKNOWN
from ..models import IST
from ..research_data.calendar import SessionCalendar
from .expectations import Expectation
from .horizon import CalendarHorizon
from .model import CheckResult, EvidenceUnknown
from .run_record import RunRecord
from .window import window_sessions

MALFORMED = (ValueError, TypeError, KeyError, AttributeError)  # a file of the wrong shape, read by one check


@dataclass(frozen=True)
class Finding:
    check: str
    session: date
    result: CheckResult


@dataclass(frozen=True)
class HealthRun:
    run_day: date
    sessions: tuple[date, ...]
    checks: tuple[str, ...]
    findings: tuple[Finding, ...]
    missed_runs: tuple[date, ...]
    warnings: tuple[str, ...] = ()  # once-only lines needing the owner (the calendar's horizon, O8b)


class HealthCheck:
    def __init__(self, expectations: list[Expectation], calendar: SessionCalendar, record: RunRecord, days: int,
                 horizon: CalendarHorizon | None = None):  # fmt: skip
        self.expectations, self.calendar, self.record, self.days = expectations, calendar, record, days
        self.horizon = horizon

    def run(self, now: datetime) -> HealthRun:
        run_day = now.astimezone(IST).date()
        sessions = window_sessions(self.calendar, run_day, self.days)
        findings = [
            Finding(e.name, session, self._result(e, session, now))
            for e in self.expectations
            for session in sessions
            if e.live_from is not None and session >= e.live_from
        ]
        return HealthRun(run_day, tuple(sessions), tuple(e.name for e in self.expectations if e.live_from),
                         tuple(findings), tuple(self.record.missing(run_day, self.days)),
                         self._warnings(run_day))  # fmt: skip

    def _warnings(self, run_day: date) -> tuple[str, ...]:
        line = self.horizon.warning(run_day) if self.horizon else None
        return (line,) if line else ()

    def _result(self, expectation: Expectation, session: date, now: datetime) -> CheckResult:
        kind = self.calendar.session_kind(session)
        if not expectation.expected_on(session, kind):
            return CheckResult(HEALTH_NOT_EXPECTED, f"{kind} session")
        try:
            return expectation.check.check(session, now)
        except EvidenceUnknown as unknown:
            return CheckResult(HEALTH_UNKNOWN, str(unknown))
        except MALFORMED as malformed:
            return CheckResult(HEALTH_UNKNOWN, f"evidence malformed ({type(malformed).__name__})")
