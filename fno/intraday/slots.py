"""The 26 marks of a session (09:15, 09:30, ..., 15:30 IST) and when a snapshot counts for its mark (story A16)."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

from ..models import IST

FIRST_MARK, MARK_STEP, MARKS_PER_SESSION = time(9, 15), timedelta(minutes=15), 26
ON_TIME_SECONDS = 120  # a mark's index answer must arrive within 2 minutes (design 5.2: older is stale)
MAX_WAIT = timedelta(minutes=15)  # a run started early waits at most this long for its mark


def marks(day: date) -> list[datetime]:
    """The session's marks, in IST: 09:15 + 15k minutes for k = 0..25 (the last is 15:30)."""
    first = datetime.combine(day, FIRST_MARK, IST)
    return [first + k * MARK_STEP for k in range(MARKS_PER_SESSION)]


def window_end(mark: datetime) -> datetime:
    return mark + timedelta(seconds=ON_TIME_SECONDS)


def takeable_marks(day: date, now: datetime) -> list[datetime]:
    """Marks a run started at `now` may still take: those whose window is open, then those at most MAX_WAIT ahead."""
    return [m for m in marks(day) if m <= now <= window_end(m) or now < m <= now + MAX_WAIT]


def label(mark: datetime) -> str:
    return f"{mark.astimezone(IST):%H:%M}"
