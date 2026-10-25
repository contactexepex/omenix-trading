"""The regular sessions FL1 counts in. G13b issues, targets and scores on regular sessions only (a special or muhurat
session is never a horizon step: `nth_regular_session`), so FL1 steps back and forward the same way over A7's
calendar; stepping over every session would find the wrong issue day around a muhurat or special session."""

from __future__ import annotations

from datetime import date, timedelta

from ..constants import SESSION_REGULAR
from ..research_data.calendar import SessionCalendar


class RegularSessions:
    def __init__(self, calendar: SessionCalendar):
        self.calendar = calendar

    def is_regular(self, day: date) -> bool:
        return self.calendar.session_kind(day) == SESSION_REGULAR

    def _step(self, day: date, direction: int) -> date:
        day += timedelta(direction)
        while not self.is_regular(day):  # stops at the calendar's covered range: session_kind raises outside it
            day += timedelta(direction)
        return day

    def previous(self, day: date) -> date:
        return self._step(day, -1)

    def next(self, day: date) -> date:
        return self._step(day, 1)

    def back(self, day: date, sessions: int) -> date:
        for _ in range(sessions):
            day = self.previous(day)
        return day

    def ahead(self, day: date, target: date) -> int:
        """Regular sessions from `day` to `target` (0 when they are the same day)."""
        count = 0
        while day < target:
            day, count = self.next(day), count + 1
        return count

    def window(self, day: date, sessions: int) -> list[date]:
        """`day` and the `sessions - 1` regular sessions before it, oldest first."""
        days = [day]
        while len(days) < sessions:
            days.append(self.previous(days[-1]))
        return days[::-1]
