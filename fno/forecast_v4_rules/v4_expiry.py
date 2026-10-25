"""V4's expiry (PROTOCOL_v4.md section 1.4; story G7b completion): the first listed NIFTY expiry with at least 5 scored
sessions in `(day, expiry]`. One rule, one place: A4e's `v4` quote window (story G10) imports it to choose which expiry
to record and names the choice in the pack as `v4_expiry`; G7b's V4 terms read that field and re-check its session
count with `scored_sessions_until`. Pure: no I/O, no clock. A day the calendar does not cover raises its
`CalendarError`, never a guessed count."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, timedelta

from ..constants import V4_RV_BELOW_WEEKLY_IV
from ..forecast_v4.sessions import is_scored_session
from ..forecast_v4.terms import HORIZON_SESSIONS
from ..research_data.calendar import SessionCalendar

V4_MIN_SESSIONS = HORIZON_SESSIONS[V4_RV_BELOW_WEEKLY_IV]  # the expiry must cover V4's whole 5-session window


def scored_sessions_until(day: date, expiry: date, calendar: SessionCalendar) -> int:
    """The A7 regular sessions in `(day, expiry]` (special and muhurat sessions are never scored, protocol 2)."""
    return sum(is_scored_session(calendar, day + timedelta(n)) for n in range(1, (expiry - day).days + 1))


def first_v4_expiry(day: date, listed_expiries: Iterable[date], calendar: SessionCalendar) -> date | None:
    """The nearest listed expiry after `day` with at least 5 scored sessions in `(day, expiry]`; None when none has.
    `listed_expiries` are the expiries listed at the cutoff, in any order (repeats ignored)."""
    calendar.session_kind(day)  # a day the calendar does not cover raises here, even with nothing listed after it
    for expiry in sorted({e for e in listed_expiries if e > day}):
        if scored_sessions_until(day, expiry, calendar) >= V4_MIN_SESSIONS:
            return expiry
    return None
