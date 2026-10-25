"""Protocol v4's close and RV baselines (PROTOCOL_v4.md section 3.1; stories G7 and G7b): base rate (V6, V7),
trailing, EWMA and HAR (V1, V2, V3). Point in time: a forecast for day `d` reads only sessions before `d` (their
closes and RVs are first seen before `d`'s cutoff; `d`'s own are not). A value that cannot be computed is missing,
never floored or replaced."""

from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass
from datetime import date
from functools import cache

import numpy as np

from .series import DayValue, Outcome, SessionRv

OK, MISSING, NOT_ELIGIBLE, NOT_STARTED = "ok", "missing", "not_eligible", "not_started"
WINDOW, MINIMUM = 750, 500  # base rate and HAR: the most recent 750 resolved rows, at least 500
EWMA_LAMBDA, EWMA_SEED = 0.94, 250  # RiskMetrics; seeded with the mean of the first 250 sessions
HAR_LAGS = (1, 5, 22)


@dataclass(frozen=True)
class Value:
    status: str
    value: float | None = None

    @classmethod
    def of(cls, value: float | None, positive: bool = True) -> Value:
        """A computed figure: missing when absent, not finite or (for a variance) not strictly positive."""
        if value is None or not np.isfinite(value) or (positive and value <= 0):
            return cls(MISSING)
        return cls(OK, float(value))


def before(days: list[date], d: date) -> int:
    """How many of the sorted days are strictly before `d`."""
    return bisect_left(days, d)


class BaseRate:
    """The share of 1s among the most recent 750 outcomes resolved before `d`'s cutoff (at least 500)."""

    def __init__(self, outcomes: list[Outcome]):
        self.outcomes = sorted(outcomes, key=lambda o: o.resolved_on)
        self.resolved = [o.resolved_on for o in self.outcomes]

    def forecast(self, d: date) -> Value:
        known = self.outcomes[max(0, before(self.resolved, d) - WINDOW) : before(self.resolved, d)]
        if len(known) < MINIMUM:
            return Value(NOT_ELIGIBLE)
        return Value.of(sum(o.value for o in known) / len(known), positive=False)


class Ewma:
    """`s2_t = 0.94 s2_(t-1) + 0.06 RV_t`, seeded at the 250th session with the mean of the first 250; the forecast
    for `d` over `h` sessions is `h x s2` at the last session before `d`."""

    def __init__(self, rv: list[DayValue]):
        self.days = [r.day for r in rv]
        self.s2: list[float | None] = [None] * len(rv)
        if len(rv) >= EWMA_SEED:
            level = float(np.mean([r.value for r in rv[:EWMA_SEED]]))
            self.s2[EWMA_SEED - 1] = level
            for i in range(EWMA_SEED, len(rv)):
                level = EWMA_LAMBDA * level + (1 - EWMA_LAMBDA) * rv[i].value
                self.s2[i] = level

    def variance(self, d: date) -> float | None:
        i = before(self.days, d) - 1
        return self.s2[i] if i >= 0 else None

    def forecast(self, d: date, horizon: int) -> Value:
        s2 = self.variance(d)
        return Value(NOT_ELIGIBLE) if s2 is None else Value.of(horizon * s2)


class Har:
    """HAR in levels: the mean RV over the next `h` sessions on an intercept and the mean RV of the last 1, 5 and 22
    sessions, fitted by OLS on the most recent 750 rows resolved before the refit day (at least 500), refit on the
    first session of each month. A row for day t uses RVs up to t-1 (what a forecast on t can know) and its target
    is the mean RV of t+1..t+h, resolved after t+h's close. `rv` holds only usable sessions (void ones dropped by the
    caller), so a row whose window spans a gap is still taken in session order."""

    def __init__(self, rv: list[DayValue], horizon: int, sessions: list[date], minimum: int = MINIMUM):
        self.rv, self.h, self.minimum = rv, horizon, minimum
        self.days = [r.day for r in rv]
        self.values = np.array([r.value for r in rv], dtype=float)
        self.sessions = sessions
        self._fit = cache(self._fit_at)

    def _features(self, end: int) -> list[float] | None:
        """Intercept and the means of the last 1, 5 and 22 values ending at index `end - 1`."""
        if end < max(HAR_LAGS):
            return None
        return [1.0] + [float(self.values[end - lag : end].mean()) for lag in HAR_LAGS]

    def refit_day(self, d: date) -> date:
        """The first session of `d`'s month (the scored-session calendar)."""
        return next(s for s in self.sessions if s.year == d.year and s.month == d.month)

    def _fit_at(self, refit: date) -> np.ndarray | None:
        rows, targets = [], []
        for t in range(1, len(self.rv) - self.h):
            if self.days[t + self.h] >= refit:  # target not resolved before the refit day's cutoff
                break
            x = self._features(t)  # RVs before day t
            if x is not None:
                rows.append(x)
                targets.append(self.values[t + 1 : t + 1 + self.h].mean())
        rows, targets = rows[-WINDOW:], targets[-WINDOW:]
        if len(rows) < self.minimum:
            return None
        return np.linalg.lstsq(np.array(rows), np.array(targets), rcond=None)[0]

    def forecast(self, d: date) -> Value:
        beta = self._fit(self.refit_day(d))
        x = self._features(before(self.days, d))
        if beta is None or x is None:
            return Value(NOT_ELIGIBLE)
        return Value.of(self.h * float(np.dot(beta, x)))


class TrailingSum:
    """V2 and V3's trailing baseline: the sum of the last `h` session RVs before `d` (the same measure; `d`'s own is
    not known at the cutoff), not eligible with fewer than `h`."""

    def __init__(self, rv: list[DayValue]):
        self.days = [r.day for r in rv]
        self.values = [r.value for r in rv]

    def forecast(self, d: date, horizon: int) -> Value:
        end = before(self.days, d)
        if end < horizon:
            return Value(NOT_ELIGIBLE)
        return Value.of(sum(self.values[end - horizon : end]))


def trailing_previous_session(rv: list[SessionRv], previous: date | None) -> Value:
    """V1's trailing baseline: the previous scored session's intraday RV, missing when that session is void or has no
    row (never an older session in its place; judge 127)."""
    row = next((r for r in rv if r.day == previous), None)
    return Value(MISSING) if row is None else Value.of(row.value)
