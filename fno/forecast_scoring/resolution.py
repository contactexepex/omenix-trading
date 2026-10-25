"""When a forecast's outcome is known (story G4; protocol section 7: "scored only when its outcome is resolved and not
void; never earlier").

Outcomes use the official NIFTY 50 and India VIX closes (`warmup_closes.csv`, which story O6 extends every trading
evening) **through the as-of day only**, so nothing after it can be read, and the targets of `targets.py` (protocol
section 2). Question 5 also needs the day's IV30 (protocol section 3, from the panel).
- **pending:** the target trading day (calendar) is after the as-of day or after the last official close, or (question
  5) the panel does not reach the forecast day yet. Never scored; scored on a later day.
- **void:** the target day is covered but a needed close is missing, or (question 5) IV30 is flagged or missing.
- **resolved:** the outcome (and, for question 5 on a flagged day, the descriptive sensitivity outcome).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import date, timedelta
from typing import NamedTuple

from ..constants import FORECAST_Q5_RV_BELOW_IV
from ..forecast.closes_source import OfficialCloses
from ..forecast.history import HORIZONS, ForecastHistory
from ..forecast.iv30 import AtmIv30
from ..forecast.targets import ForecastTargets, daily_closes
from ..research_data.calendar import SessionCalendar

RESOLVED, PENDING, VOID = "resolved", "pending", "void"


class Resolution(NamedTuple):
    status: str
    outcome: bool | None = None  # the primary outcome when resolved
    flagged_outcome: bool | None = None  # question 5 on a flagged-IV30 day: the descriptive sensitivity outcome


class OutcomeResolver(ABC):
    @abstractmethod
    def resolve(self, question: str, day: date) -> Resolution:
        """The outcome of `question` for forecast day `day` as known on the resolver's as-of day."""


class CloseDay(NamedTuple):
    day: date
    underlying: float | None
    vix: float | None


class OfficialOutcomes(OutcomeResolver):
    """Outcomes from the official closes through `as_of`; question 5's IV30 from `iv30(day)` (None: panel not there)."""

    def __init__(
        self,
        closes: OfficialCloses,
        calendar: SessionCalendar,
        as_of: date,
        iv30: Callable[[date], tuple[bool, AtmIv30 | None]],
        horizon_day: Callable[[date, int], date | None],
    ):
        known = closes.through(as_of + timedelta(days=1))  # `through` excludes its own day; the as-of close counts
        self.last_close = max(known) if known else None
        rows = [CloseDay(day, nifty, vix) for day, (nifty, vix) in known.items()]
        self.targets = ForecastTargets(daily_closes(calendar, min(known), self.last_close, rows)) if known else None
        self.iv30, self.horizon_day = iv30, horizon_day

    def resolve(self, question: str, day: date) -> Resolution:
        target = self.horizon_day(day, HORIZONS[question])
        if self.targets is None or target is None or target > self.last_close:
            return Resolution(PENDING)
        if question != FORECAST_Q5_RV_BELOW_IV:
            outcome = self.targets.outcome(question, day)
            return Resolution(VOID) if outcome is None else Resolution(RESOLVED, outcome)
        covered, iv30 = self.iv30(day)
        if not covered:
            return Resolution(PENDING)
        primary, flagged = self.targets.rv_below_iv(day, iv30), self.targets.rv_below_iv_flagged(day, iv30)
        return Resolution(VOID, None, flagged) if primary is None else Resolution(RESOLVED, primary)


def panel_iv30(history: ForecastHistory) -> Callable[[date], tuple[bool, AtmIv30 | None]]:
    """IV30 of a day from the panel: (covered, value); a day after the panel's last session is not covered yet."""
    last = max(s.day for s in history.panel.sessions)
    return lambda day: (day <= last, history.iv30(day))
