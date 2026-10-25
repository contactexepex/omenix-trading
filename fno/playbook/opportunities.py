"""Which (strategy version, expiry) is an opportunity today (story D2; E2's common opportunity set uses the same code):
the first trading day on which a monthly expiry is within the version's day window, with the time exit at the last
trading day at least `exit_days_before_expiry` days before the expiry (experiment 1's decision day and exit)."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta

from ..research_engine.cycles import TradingDays
from ..research_engine.features import DecisionContext
from .schema import Strategy

BOOK, SHADOW = "book", "shadow"  # allocated to the book's account / evaluated and recorded only (owner, 14 Oct 2026)


@dataclass(frozen=True)
class Opportunity:
    strategy: Strategy
    context: DecisionContext
    mode: str  # BOOK or SHADOW

    @property
    def opportunity_id(self) -> str:
        return f"{self.strategy.name}-v{self.strategy.version}:{self.context.expiry.isoformat()}"


class OpportunityFinder:
    def __init__(self, days: TradingDays):
        self.days = days

    def find(self, strategy: Strategy, day: date, monthly_expiries: Iterable[date], mode: str) -> list[Opportunity]:
        if not self.days.is_trading_day(day):
            return []
        rule = strategy.structure.expiry
        found = []
        for expiry in sorted(set(monthly_expiries)):
            if self._first_day_in_window(day, expiry, rule.min_days, rule.max_days):
                found.append(Opportunity(strategy, DecisionContext(expiry, day, self.exit_day(strategy, expiry)), mode))
        return found

    def exit_day(self, strategy: Strategy, expiry: date) -> date:
        """The version's time exit for this expiry: the last trading day at least `exit_days_before_expiry` days
        before it (also what Book 1's exit review applies to an open trade, story E5)."""
        return self.days.last_on_or_before(expiry - timedelta(days=strategy.structure.expiry.exit_days_before_expiry))

    def _first_day_in_window(self, day: date, expiry: date, low: int, high: int) -> bool:
        if not low <= (expiry - day).days <= high:
            return False
        return (expiry - self._previous(day)).days > high

    def _previous(self, day: date) -> date:
        day -= timedelta(days=1)
        while not self.days.is_trading_day(day):
            day -= timedelta(days=1)
        return day
