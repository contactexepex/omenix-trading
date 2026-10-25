"""The five forecast questions' outcomes, by reference functions (story G1; research/forecasts/PROTOCOL.md section 2).

Trading days are the NSE session calendar's sessions (story A7) without muhurat sessions (Diwali's one-hour evening
session is not a normal daily close; as story B1). "Today" is the forecast day `d`, itself a trading day; "in n trading
days" is the n-th trading day after `d`. Closes are the NIFTY 50 and India VIX closes of NSE's index-close file (story
A3). Realised volatility is B1's: root mean square of daily log returns, not demeaned, times sqrt(252), in points.
An outcome is `None` (void, never scored) when the forecast day is not a trading day, the target day is beyond the
calendar or the data, or any close it needs is missing; never a guess.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from datetime import date

from ..constants import (
    FORECAST_Q1_UP_20D,
    FORECAST_Q2_MOVE_3PCT_20D,
    FORECAST_Q3_RV_RISES_20D,
    FORECAST_Q4_VIX_UP_10D,
    FORECAST_Q5_RV_BELOW_IV,
    SESSION_MUHURAT,
)
from ..research_data.calendar import SessionCalendar
from ..research_engine.close_series import realised_vol_points
from .iv30 import AtmIv30

PRICE_HORIZON = 20  # trading days, questions 1, 2, 3 and 5
VIX_HORIZON = 10  # trading days, question 4
MOVE_THRESHOLD = 0.03  # question 2: |simple return| at least 3%
RV_RETURNS = 20  # daily log returns in each realised volatility (21 closes)


class DailyCloses:
    """Trading days in order with their closes (None when the day's close is missing)."""

    def __init__(self, days: tuple[date, ...], nifty: Mapping[date, float | None], vix: Mapping[date, float | None]):
        self.days, self.nifty, self.vix = tuple(days), nifty, vix
        self._index = {day: i for i, day in enumerate(self.days)}

    def offset(self, day: date, sessions: int) -> date | None:
        """The trading day `sessions` after (or, negative, before) `day`; None outside the known days."""
        i = self._index.get(day)
        if i is None or not 0 <= i + sessions < len(self.days):
            return None
        return self.days[i + sessions]

    def window(self, day: date, start: int, end: int) -> list[float | None] | None:
        """NIFTY closes from `start` to `end` trading days after `day` (both included); None if any day is unknown."""
        first, last = self.offset(day, start), self.offset(day, end)
        if first is None or last is None:
            return None
        i = self._index[first]
        return [self.nifty.get(d) for d in self.days[i : i + end - start + 1]]


def trading_days(calendar: SessionCalendar, start: date, end: date) -> tuple[date, ...]:
    """The calendar's sessions from start to end, muhurat sessions left out."""
    return tuple(d for d in calendar.sessions(start, end) if calendar.session_kind(d) != SESSION_MUHURAT)


def daily_closes(calendar: SessionCalendar, start: date, end: date, closes: Iterable) -> DailyCloses:
    """`closes`: items with `day`, `underlying` (NIFTY 50) and `vix` (e.g. the panel's `SessionClose`)."""
    by_day = {c.day: c for c in closes}
    days = trading_days(calendar, start, end)
    nifty = {d: by_day[d].underlying if d in by_day else None for d in days}
    vix = {d: by_day[d].vix if d in by_day else None for d in days}
    return DailyCloses(days, nifty, vix)


def _valid(*values: float | None) -> bool:
    return all(v is not None and v > 0 for v in values)


class ForecastTargets:
    def __init__(self, closes: DailyCloses):
        self.closes = closes

    def _nifty_pair(self, day: date, horizon: int) -> tuple[float, float] | None:
        target = self.closes.offset(day, horizon)
        today, later = self.closes.nifty.get(day), self.closes.nifty.get(target) if target else None
        return (today, later) if target and _valid(today, later) else None

    def nifty_up(self, day: date) -> bool | None:
        """Q1: NIFTY close 20 trading days after `day` strictly above `day`'s close (equal is no)."""
        pair = self._nifty_pair(day, PRICE_HORIZON)
        return None if pair is None else pair[1] > pair[0]

    def nifty_moves_3pct(self, day: date) -> bool | None:
        """Q2: |close 20 trading days later / close today - 1| at least 3%."""
        pair = self._nifty_pair(day, PRICE_HORIZON)
        return None if pair is None else abs(pair[1] / pair[0] - 1) >= MOVE_THRESHOLD

    def trailing_rv(self, day: date) -> float | None:
        """Realised volatility of the 20 daily returns ending at `day`'s close (21 closes), in points."""
        window = self.closes.window(day, -RV_RETURNS, 0)
        return None if window is None else realised_vol_points(window, RV_RETURNS)

    def next_rv(self, day: date) -> float | None:
        """Realised volatility of the 20 daily returns from `day`'s close to the close 20 trading days later."""
        window = self.closes.window(day, 0, PRICE_HORIZON)
        return None if window is None else realised_vol_points(window, RV_RETURNS)

    def rv_rises(self, day: date) -> bool | None:
        """Q3: next-20-day realised volatility strictly above the trailing 20-day realised volatility today."""
        later, trailing = self.next_rv(day), self.trailing_rv(day)
        return None if later is None or trailing is None else later > trailing

    def vix_up(self, day: date) -> bool | None:
        """Q4: India VIX close 10 trading days after `day` strictly above `day`'s close."""
        target = self.closes.offset(day, VIX_HORIZON)
        today, later = self.closes.vix.get(day), self.closes.vix.get(target) if target else None
        return later > today if target and _valid(today, later) else None

    def rv_below_iv(self, day: date, iv30: AtmIv30 | None) -> bool | None:
        """Q5, primary: next-20-day realised volatility strictly below `day`'s 30-day ATM implied volatility (both in
        points). Void when IV30 is missing or flagged (a single-expiry fallback is an approximation, review 28)."""
        return None if iv30 is None or iv30.flagged else self._rv_below(day, iv30.points)

    def rv_below_iv_flagged(self, day: date, iv30: AtmIv30 | None) -> bool | None:
        """Q5's descriptive sensitivity: the same comparison, only on days whose IV30 is flagged; never confirmatory."""
        return self._rv_below(day, iv30.points) if iv30 is not None and iv30.flagged else None

    def _rv_below(self, day: date, iv30_points: float) -> bool | None:
        later = self.next_rv(day)
        return None if later is None else later < iv30_points

    def outcome(self, question: str, day: date, iv30: AtmIv30 | None = None) -> bool | None:
        rules: dict[str, Callable[[date], bool | None]] = {
            FORECAST_Q1_UP_20D: self.nifty_up,
            FORECAST_Q2_MOVE_3PCT_20D: self.nifty_moves_3pct,
            FORECAST_Q3_RV_RISES_20D: self.rv_rises,
            FORECAST_Q4_VIX_UP_10D: self.vix_up,
            FORECAST_Q5_RV_BELOW_IV: lambda d: self.rv_below_iv(d, iv30),
        }
        if question not in rules:
            raise ValueError(f"unknown forecast question {question!r}")
        return rules[question](day)
