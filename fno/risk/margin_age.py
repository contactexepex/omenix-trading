"""How old a margin row may be (story C2, changed by C5): one strategy per profile.

The Manual paper account keeps C2's rule of 13 Oct 2026, a row at most `max_age_days` calendar days old. The books
follow design 6.1a (story C5): margin data older than one session means no new entry, so a row is fresh only when it
is dated on or after the trading day `sessions` trading days before the decision day (one: the previous trading day's
row, or the day's own). Trading days are A14's (`TradingDays`: regular and special sessions, never a muhurat-only
session, for which A14 writes no row; judge 105). A weekend, holiday or muhurat Sunday never ages a row; a missed
trading day's row always does.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, timedelta

from ..research_engine.cycles import TradingDays


class MarginAge(ABC):
    @abstractmethod
    def fresh(self, as_of: date, day: date) -> bool:
        """Whether a margin row dated `as_of` may be used on `day` (as_of is on or before day)."""

    @abstractmethod
    def limit(self) -> str:
        """The rule in words, for the refusal reason."""


class DaysOld(MarginAge):
    def __init__(self, max_days: int):
        self.max_days = max_days

    def fresh(self, as_of: date, day: date) -> bool:
        return (day - as_of).days <= self.max_days

    def limit(self) -> str:
        return f"older than {self.max_days} days"


class SessionsOld(MarginAge):
    def __init__(self, days: TradingDays, sessions: int):
        self.days, self.sessions = days, sessions

    def oldest(self, day: date) -> date:
        """The oldest usable row date: the trading day `sessions` trading days before `day`."""
        for _ in range(self.sessions):
            day = self.days.last_on_or_before(day - timedelta(days=1))
        return day

    def fresh(self, as_of: date, day: date) -> bool:
        return as_of >= self.oldest(day)

    def limit(self) -> str:
        return f"older than {self.sessions} session(s)"
