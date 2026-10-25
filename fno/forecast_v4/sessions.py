"""v4's session set (PROTOCOL_v4.md section 2): only A7's `regular` sessions are scored sessions. Muhurat sessions
(about an hour, in the evening) and weekend `special` sessions are never a scored session, a horizon step or a base-rate
return; a return spans from one regular session's close to the next regular session's close, so a special session's
move is inside the following regular return, never dropped."""

from __future__ import annotations

from datetime import date, timedelta

from ..constants import SESSION_REGULAR
from ..research_data.calendar import SessionCalendar


def is_scored_session(calendar: SessionCalendar, day: date) -> bool:
    return calendar.session_kind(day) == SESSION_REGULAR


def next_scored_sessions(calendar: SessionCalendar, day: date, count: int) -> list[date]:
    """The `count` regular sessions after `day` (the horizon of a forecast made on `day`)."""
    found: list[date] = []
    while len(found) < count:
        day += timedelta(1)
        if is_scored_session(calendar, day):
            found.append(day)
    return found
