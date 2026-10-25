"""The target session of each horizon (G13 section 3): `h1` and `h5` count regular sessions after the day on the
NSE calendar (A7); `e1` and `e2` are the first and second chain expiries after the day. A target past the calendar's
last year is not eligible (never guessed)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from ..constants import SESSION_REGULAR
from ..research_data.calendar import CalendarError, SessionCalendar
from .constants import E1, E2, SESSION_HORIZONS

CALENDAR_ENDS = "the session calendar ends before the target ({error})"
NO_EXPIRY = "no {which} expiry after the day in the chain"
NOT_A_SESSION = "expiry {expiry} is not a regular session"


@dataclass(frozen=True)
class Target:
    horizon: str
    day: date | None
    sessions: int | None  # regular sessions after the forecast day, up to and including the target
    expiry: date | None = None
    reason: str | None = None  # why there is no target


def _is_regular(calendar: SessionCalendar, day: date) -> bool:
    return calendar.session_kind(day) == SESSION_REGULAR


def regular_sessions_until(calendar: SessionCalendar, day: date, end: date) -> int:
    count, current = 0, day
    while current < end:
        current += timedelta(days=1)
        count += _is_regular(calendar, current)
    return count


def previous_regular_session(calendar: SessionCalendar, day: date) -> date:
    current = day - timedelta(days=1)
    while not _is_regular(calendar, current):
        current -= timedelta(days=1)
    return current


def nth_regular_session(calendar: SessionCalendar, day: date, n: int) -> date:
    current, found = day, 0
    while found < n:
        current += timedelta(days=1)
        found += _is_regular(calendar, current)
    return current


def targets(calendar: SessionCalendar, day: date, expiries: list[date]) -> dict[str, Target]:
    found = {}
    for horizon, n in SESSION_HORIZONS.items():
        try:
            found[horizon] = Target(horizon, nth_regular_session(calendar, day, n), n)
        except CalendarError as error:
            found[horizon] = Target(horizon, None, None, reason=CALENDAR_ENDS.format(error=error))
    after = sorted(e for e in expiries if e > day)
    for index, (horizon, which) in enumerate(((E1, "near"), (E2, "next"))):
        found[horizon] = _expiry_target(calendar, day, horizon, after[index] if len(after) > index else None, which)
    return found


def _expiry_target(calendar: SessionCalendar, day: date, horizon: str, expiry: date | None, which: str) -> Target:
    if expiry is None:
        return Target(horizon, None, None, reason=NO_EXPIRY.format(which=which))
    try:
        if not _is_regular(calendar, expiry):
            return Target(horizon, None, None, expiry, NOT_A_SESSION.format(expiry=expiry))
        return Target(horizon, expiry, regular_sessions_until(calendar, day, expiry), expiry)
    except CalendarError as error:
        return Target(horizon, None, None, expiry, CALENDAR_ENDS.format(error=error))
