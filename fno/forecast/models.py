"""Baseline (c) of the frozen forecast protocol (story G2; PROTOCOL.md section 4): simple statistical models for
questions 3, 4 and 5, point-in-time.

Ordinary least squares with an intercept on the most recent 750 trading days `t` before the refit day whose target was
known before the refit day (at least 500 rows, else no forecast). **Refit schedule:** the first trading day of each
calendar month; the fit (coefficients and residuals) serves every day of that month. Probabilities come from the
fit's own residuals `e` (their empirical distribution), never from a normal assumption:
- Q3 and Q5 (HAR-type): `y_t = ln next RV(t)`, regressors `ln RV5(t)`, `ln RV20(t)`, `ln RV60(t)`; Q3 = share of
  `y_hat + e > ln trailing RV(d)`, Q5 = share of `y_hat + e < ln IV30(d)`.
- Q4 (VIX mean reversion): `y_t = ln(VIX(t+10) / VIX(t))`, regressor `ln VIX(t)` minus the mean of `ln VIX` over the 250
  trading days ending at `t`; Q4 = share of `y_hat + e > 0`.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date

import numpy

from ..constants import (
    BASELINE_MODEL,
    FORECAST_Q3_RV_RISES_20D,
    FORECAST_Q4_VIX_UP_10D,
    FORECAST_Q5_RV_BELOW_IV,
    FORECAST_QUESTIONS,
)
from ..research_engine.close_series import realised_vol_points
from .baselines import Probabilities
from .history import ForecastHistory
from .targets import PRICE_HORIZON, VIX_HORIZON

MODEL_WINDOW, MODEL_MINIMUM = 750, 500
HAR_RETURNS = (5, 20, 60)
VIX_MEAN_DAYS = 250

Row = tuple[float, ...]


@dataclass(frozen=True)
class Fit:
    coefficients: numpy.ndarray  # intercept first
    residuals: numpy.ndarray

    def predict(self, x: Row) -> float:
        return float(self.coefficients[0] + numpy.dot(self.coefficients[1:], x))


def fit_ols(xs: Sequence[Row], ys: Sequence[float]) -> Fit:
    design = numpy.column_stack([numpy.ones(len(xs)), numpy.asarray(xs, dtype=float)])
    target = numpy.asarray(ys, dtype=float)
    coefficients, *_ = numpy.linalg.lstsq(design, target, rcond=None)
    return Fit(coefficients, target - design @ coefficients)


def share(values: numpy.ndarray, keep: Callable[[numpy.ndarray], numpy.ndarray]) -> float:
    return float(numpy.mean(keep(values)))


def _log(value: float | None) -> float | None:
    return math.log(value) if value is not None and value > 0 else None


class ModelBaseline:
    name = BASELINE_MODEL

    def __init__(self, history: ForecastHistory, window: int = MODEL_WINDOW, minimum: int = MODEL_MINIMUM):
        self.history, self.window, self.minimum = history, window, minimum
        self._fits: dict[tuple[str, date], Fit | None] = {}

    def refit_day(self, day: date) -> date:
        """The first trading day of `day`'s calendar month (the refit schedule)."""
        return next(t for t in self.history.days if t.year == day.year and t.month == day.month)

    def har_x(self, day: date) -> Row | None:
        closes = self.history.closes
        window = closes.window(day, -max(HAR_RETURNS), 0)
        if window is None:
            return None
        logs = [_log(realised_vol_points(window, n)) for n in HAR_RETURNS]
        return None if None in logs else tuple(logs)

    def har_y(self, day: date) -> float | None:
        return _log(self.history.targets.next_rv(day))

    def vix_x(self, day: date) -> Row | None:
        h = self.history
        start = h.closes.offset(day, -(VIX_MEAN_DAYS - 1))
        if start is None:
            return None
        values = [_log(h.closes.vix.get(t)) for t in h.days[h.index[start] : h.index[day] + 1]]
        return None if None in values else (values[-1] - sum(values) / len(values),)

    def vix_y(self, day: date) -> float | None:
        vix = self.history.closes.vix
        later = self.history.closes.offset(day, VIX_HORIZON)
        return None if later is None else _log_ratio(vix.get(later), vix.get(day))

    def _spec(self, question: str) -> tuple[Callable, Callable, int]:
        if question == FORECAST_Q4_VIX_UP_10D:
            return self.vix_x, self.vix_y, VIX_HORIZON
        return self.har_x, self.har_y, PRICE_HORIZON

    def fit(self, question: str, day: date) -> Fit | None:
        """The fit serving `day`: made on its month's refit day from rows known before that day."""
        key = ("q4" if question == FORECAST_Q4_VIX_UP_10D else "har", self.refit_day(day))
        if key not in self._fits:
            self._fits[key] = self._fit_on(question, key[1])
        return self._fits[key]

    def _fit_on(self, question: str, refit: date) -> Fit | None:
        x_of, y_of, horizon = self._spec(question)
        xs, ys = [], []
        for t in self.history.earlier(refit):
            known_on = self.history.closes.offset(t, horizon)
            if known_on is None or known_on >= refit:
                continue
            x, y = x_of(t), y_of(t)
            if x is not None and y is not None:
                xs.append(x)
                ys.append(y)
                if len(xs) == self.window:
                    break
        return fit_ols(xs, ys) if len(xs) >= self.minimum else None

    def probability(self, question: str, day: date) -> float | None:
        x_of, _, _ = self._spec(question)
        fit, x = self.fit(question, day), x_of(day)
        if fit is None or x is None:
            return None
        predicted = fit.predict(x) + fit.residuals
        if question == FORECAST_Q4_VIX_UP_10D:
            return share(predicted, lambda v: v > 0)
        if question == FORECAST_Q3_RV_RISES_20D:
            threshold = _log(self.history.targets.trailing_rv(day))
            return None if threshold is None else share(predicted, lambda v: v > threshold)
        iv30 = self.history.iv30(day)
        threshold = _log(iv30.points if iv30 else None)
        return None if threshold is None else share(predicted, lambda v: v < threshold)

    def probabilities(self, day: date) -> Probabilities:
        out: Probabilities = dict.fromkeys(FORECAST_QUESTIONS)
        for question in (FORECAST_Q3_RV_RISES_20D, FORECAST_Q4_VIX_UP_10D, FORECAST_Q5_RV_BELOW_IV):
            out[question] = self.probability(question, day)
        return out


def _log_ratio(later: float | None, today: float | None) -> float | None:
    return math.log(later / today) if later and today and later > 0 and today > 0 else None
