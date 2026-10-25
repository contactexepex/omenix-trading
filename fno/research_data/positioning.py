"""Participant open interest as a decision could have known it (story A8): the latest file the availability rule lets a
decision at a given moment use, never one NSE had not yet published."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime

from .availability import AvailabilityRule
from .calendar import SessionCalendar
from .participant_oi import ParticipantOi, read_participant_oi

LOOKBACK_SESSIONS = 5  # an older file is too stale to stand in for the latest one


class PointInTimeParticipantOi:
    def __init__(
        self,
        file_for: Callable[[date], bytes | None],
        filename_for: Callable[[date], str],
        calendar: SessionCalendar,
        rule: AvailabilityRule,
    ):
        self.file_for, self.filename_for, self.calendar, self.rule = file_for, filename_for, calendar, rule

    def as_of(self, decision_moment: datetime) -> ParticipantOi | None:
        """The newest usable file within the look-back, or None. Its `day` shows how old it is."""
        day = decision_moment.date()
        if not self.calendar.is_session(day):
            day = self.calendar.previous_session(day)
        for _ in range(LOOKBACK_SESSIONS):
            if self.rule.is_usable(day, decision_moment):
                data = self.file_for(day)
                if data is not None:
                    return read_participant_oi(data, self.filename_for(day), day)
            day = self.calendar.previous_session(day)
        return None
