"""When a session's file was public (story A23, criterion 2): from the first trading session whose 09:15 IST open is at
or after the file's write time (NSE's `Last-Modified`). A file written on its evening is available from the next
session; one whose write time is after that session's open was rewritten later (the bytes we hold may differ from what
was first public) and is available only from the session after its write, flagged `rewritten`. No write time at all
is `rewritten` too (unknown), available from the next session."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, time

from ..models import IST

SESSION_OPEN = time(9, 15)


@dataclass(frozen=True)
class Availability:
    available_from: date
    rewritten: bool


def availability(day: date, written: datetime | None, next_session: Callable[[date], date]) -> Availability:
    """`next_session`: the first trading session after a day (A7's calendar, muhurat-only evenings stepped over)."""
    first = next_session(day)
    if written is None:
        return Availability(first, True)
    session = first
    while datetime.combine(session, SESSION_OPEN, IST) < written:
        session = next_session(session)
    return Availability(session, session != first)
