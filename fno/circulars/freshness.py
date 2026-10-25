"""When a well-formed circular list is still a broken source (story A20b, judge 353 SF5): a strategy per feed."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, timedelta

from ..research_data.calendar import CalendarError, SessionCalendar
from .model import Circular, Problem

NSE_STALE = "{source}: stale: no circular dated the previous session {session} (NSE issued some on every 2026 session)"
SEBI_MAX_AGE = timedelta(days=45)  # twice the longest gap (22 days) between the 25 circulars on its page, 16 Oct 2026
SEBI_STALE = "{source}: stale: its newest circular is from {newest}, over {days} days ago"
STALE_KEY = "{source}:stale"
NO_CALENDAR = "{source}: freshness not judged: NSE's calendar does not cover {day} (add NSE's holiday circular rows)"


class PreviousSessionFreshness:
    """Fresh when the list holds a circular dated the previous session of NSE's calendar (judged any day)."""

    def __init__(self, calendar: SessionCalendar):
        self.calendar = calendar

    def __call__(self, source: str, listed: Sequence[Circular], today: date) -> Problem | None:
        try:
            session = self.calendar.previous_session(today)
        except CalendarError:  # the capture goes on; the gap in the calendar is its own problem
            return Problem(f"{source}:calendar", NO_CALENDAR.format(source=source, day=today))
        if any(c.issued_on == session for c in listed):
            return None
        return Problem(STALE_KEY.format(source=source), NSE_STALE.format(source=source, session=session))


class NewestAgeFreshness:
    """Fresh when the newest circular listed is at most `max_age` old."""

    def __init__(self, max_age: timedelta = SEBI_MAX_AGE):
        self.max_age = max_age

    def __call__(self, source: str, listed: Sequence[Circular], today: date) -> Problem | None:
        newest = max((c.issued_on for c in listed), default=None)
        if newest is not None and today - newest <= self.max_age:
            return None
        text = SEBI_STALE.format(source=source, newest=newest or "none", days=self.max_age.days)
        return Problem(STALE_KEY.format(source=source), text)
