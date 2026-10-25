"""When a decision may first use a file published after a session (story A8): the point-in-time rule that keeps a
decision on day D from seeing a file NSE had not yet published.

Two rules behind one interface. Until release times are measured, the default applies: a day's file is usable only
from the next session's decision time. With enough measured days (`MeasuredReleaseRule`), the lag is counted in
sessions, not hours (a weekend must not hide a late file): for each measured day, the first decision at or after the
file was first seen plus a safety margin; the rule uses the largest lag seen, which can be stricter than the default.

Either rule can be wrapped by `LastWriteBoundRule`: NSE rewrites some archive files after publishing them (105 of
1,929 participant-OI files, judge 15), so the bytes held today are usable no earlier than their own recorded last write.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, datetime, time, timedelta

from ..models import IST
from .calendar import SessionCalendar

SAFETY_MARGIN = timedelta(minutes=30)  # a release a little later than any measured one must still be covered


def decision_at(calendar: SessionCalendar, day: date, lag: int, decision_time: time) -> datetime:
    """The decision moment `lag` sessions after session `day` (0: that day's own decision)."""
    for _ in range(lag):
        day = calendar.next_session(day)
    return datetime.combine(day, decision_time, IST)


def sessions_until_usable(calendar: SessionCalendar, day: date, first_seen: datetime, decision_time: time) -> int:
    """How many sessions after `day` the first decision at or after `first_seen` plus the margin falls."""
    lag = 0
    while decision_at(calendar, day, lag, decision_time) < first_seen + SAFETY_MARGIN:
        lag += 1
    return lag


class AvailabilityRule(ABC):
    @abstractmethod
    def usable_from(self, day: date) -> datetime:
        """The first decision moment (IST) that may use the file published for session `day`."""

    @abstractmethod
    def describe(self) -> str:
        """One line saying which rule this is and what it rests on."""

    def is_usable(self, day: date, decision_moment: datetime) -> bool:
        return decision_moment >= self.usable_from(day)


class NextSessionRule(AvailabilityRule):
    """The default until release times are measured: usable from the next session's decision time."""

    def __init__(self, calendar: SessionCalendar, decision_time: time):
        self.calendar, self.decision_time = calendar, decision_time

    def usable_from(self, day: date) -> datetime:
        return decision_at(self.calendar, day, 1, self.decision_time)

    def describe(self) -> str:
        return f"next session at {self.decision_time:%H:%M} IST (the default until release times are measured)"


class MeasuredReleaseRule(AvailabilityRule):
    """From measured release times: usable `lag` sessions after the file's day, at the decision time."""

    def __init__(self, calendar: SessionCalendar, decision_time: time, lag: int):
        self.calendar, self.decision_time, self.lag = calendar, decision_time, lag

    def usable_from(self, day: date) -> datetime:
        return decision_at(self.calendar, day, self.lag, self.decision_time)

    def describe(self) -> str:
        return f"measured: {self.lag} session(s) after the file's day at {self.decision_time:%H:%M} IST"


class LastWriteBoundRule(AvailabilityRule):
    """Wraps a rule for files the source rewrote after publishing: the bytes held today are usable no earlier than
    the first decision at or after their recorded last write plus the margin, nor earlier than the wrapped rule
    allows. A rewritten day's numbers may differ from what was public at the time, so they wait for their own write."""

    def __init__(
        self, rule: AvailabilityRule, calendar: SessionCalendar, decision_time: time, last_written: dict[date, datetime]
    ):
        self.rule, self.calendar, self.decision_time = rule, calendar, decision_time
        self.last_written = last_written

    def usable_from(self, day: date) -> datetime:
        allowed = self.rule.usable_from(day)
        written = self.last_written.get(day)
        if written is None:
            return allowed
        lag = sessions_until_usable(self.calendar, day, written, self.decision_time)
        return max(allowed, decision_at(self.calendar, day, lag, self.decision_time))

    def describe(self) -> str:
        return (
            f"{self.rule.describe()}; no earlier than each file's recorded last write ({len(self.last_written)} days)"
        )
