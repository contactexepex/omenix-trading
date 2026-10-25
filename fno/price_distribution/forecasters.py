"""NIFTY's price-distribution forecasters (G13 section 3), each the log return `ln(close at target / S_ref)` at the
seven levels: `implied` from the expiry's risk-neutral distribution, `rv20` lognormal at the last 20 closes' realised
volatility, `hist750` the empirical h-session returns of the last 750 sessions. The AI books are slots only."""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from statistics import NormalDist

import numpy as np

from ..forecast_v4_rules.series import DayValue
from .constants import (
    E1,
    E2,
    FORECAST_LEVELS,
    HIST750,
    HIST_MINIMUM,
    HIST_WINDOW,
    IMPLIED,
    MISSING,
    NOT_ELIGIBLE,
    OK,
    RV20,
    RV_WINDOW,
    RV_YEAR,
    TAIL,
)
from .horizons import Target
from .valuation import DayValuation, ExpiryValuation

NO_DISTRIBUTION = "no implied distribution for expiry {expiry}"
NO_EXPIRY_FOR_HORIZON = "no expiry with a distribution and at least {h} sessions to it"
TOO_FEW_CLOSES = "{n} closes before the day ({minimum} needed)"
TOO_FEW_RETURNS = "{n} {h}-session returns in the last {window} sessions ({minimum} needed)"
NOT_INCREASING = "quantiles not strictly increasing"
Z = [NormalDist().inv_cdf(level) for level in FORECAST_LEVELS]


@dataclass(frozen=True)
class ForecastInputs:
    day: date
    s_ref: float
    valuation: DayValuation | None
    closes: tuple[DayValue, ...]  # regular closes strictly before the day, in date order
    sessions_to_expiry: dict[date, int] = field(default_factory=dict)


@dataclass(frozen=True)
class Forecast:
    status: str
    reason: str | None = None
    log_quantiles: tuple[float, ...] | None = None  # at FORECAST_LEVELS
    tail_levels: tuple[float, ...] = ()


def ok(log_quantiles, tails=()) -> Forecast:
    values = tuple(float(v) for v in log_quantiles)
    if any(b <= a for a, b in zip(values, values[1:], strict=False)):
        return Forecast(MISSING, NOT_INCREASING)
    return Forecast(OK, None, values, tuple(tails))


class QuantileForecaster(ABC):
    name: str
    reads_closes = False  # True: the closes must reach the previous regular session (G13 section 7)

    def forecast(self, inputs: ForecastInputs, target: Target) -> Forecast:
        if target.day is None:
            return Forecast(NOT_ELIGIBLE, target.reason)
        return self._forecast(inputs, target)

    @abstractmethod
    def _forecast(self, inputs: ForecastInputs, target: Target) -> Forecast: ...


class ImpliedForecaster(QuantileForecaster):
    """Expiry horizons read their expiry's quantiles; `h1`/`h5` take the shortest usable expiry with `n >= h`
    sessions and scale around its median: centring by `h/n`, spread by `sqrt(h/n)` (judge 304 minor 2)."""

    name = IMPLIED

    def _forecast(self, inputs: ForecastInputs, target: Target) -> Forecast:
        usable = inputs.valuation.usable() if inputs.valuation is not None else []
        if target.horizon in (E1, E2):
            expiry = next((e for e in usable if e.expiry == target.expiry), None)
            if expiry is None:
                return Forecast(MISSING, NO_DISTRIBUTION.format(expiry=target.expiry))
            return self._scaled(inputs, expiry, 1.0)
        h = target.sessions
        for expiry in usable:
            n = inputs.sessions_to_expiry.get(expiry.expiry)
            if n is not None and n >= h:
                return self._scaled(inputs, expiry, h / n)
        return Forecast(MISSING, NO_EXPIRY_FOR_HORIZON.format(h=h))

    @staticmethod
    def _scaled(inputs: ForecastInputs, expiry: ExpiryValuation, share: float) -> Forecast:
        found, forward = expiry.distribution.distribution, expiry.forward
        median = math.log(found.quantile(0.5)[0] / forward)
        carry = math.log(forward / inputs.s_ref)
        quantiles = [found.quantile(level) for level in FORECAST_LEVELS]
        values = [share * (carry + median) + math.sqrt(share) * (math.log(k / forward) - median) for k, _ in quantiles]
        tails = [level for level, (_, source) in zip(FORECAST_LEVELS, quantiles, strict=True) if source == TAIL]
        return ok(values, tails)


def log_returns(closes: tuple[DayValue, ...], step: int) -> list[float]:
    return [math.log(b.value / a.value) for a, b in zip(closes, closes[step:], strict=False)]


def daily_realised_variance(closes: tuple[DayValue, ...]) -> float | None:
    """`rv20`'s daily variance: the mean square of the last 20 daily log returns (not demeaned); None under 21 closes.
    Public for G13b's `rv20` (one rule, imported)."""
    window = closes[-(RV_WINDOW + 1) :]
    if len(window) < RV_WINDOW + 1:
        return None
    return sum(r * r for r in log_returns(window, 1)) / RV_WINDOW


class RealisedVolForecaster(QuantileForecaster):
    """Lognormal, zero log drift, at B1's realised volatility (root mean square of daily log returns, not demeaned)."""

    name = RV20
    reads_closes = True

    def _forecast(self, inputs: ForecastInputs, target: Target) -> Forecast:
        variance = daily_realised_variance(inputs.closes)
        if variance is None:
            return Forecast(NOT_ELIGIBLE, TOO_FEW_CLOSES.format(n=len(inputs.closes), minimum=RV_WINDOW + 1))
        return ok([z * math.sqrt(variance) * math.sqrt(target.sessions) for z in Z])


class HistoricalForecaster(QuantileForecaster):
    """The empirical quantiles (numpy's linear rule) of every h-session log return inside the last 750 closes."""

    name = HIST750
    reads_closes = True

    def _forecast(self, inputs: ForecastInputs, target: Target) -> Forecast:
        returns = log_returns(inputs.closes[-HIST_WINDOW:], target.sessions)
        if len(returns) < HIST_MINIMUM:
            reason = TOO_FEW_RETURNS.format(n=len(returns), h=target.sessions, window=HIST_WINDOW,
                                            minimum=HIST_MINIMUM)  # fmt: skip
            return Forecast(NOT_ELIGIBLE, reason)
        return ok(np.quantile(np.array(returns), FORECAST_LEVELS))


def realised_vol_points(closes: tuple[DayValue, ...]) -> float | None:
    """`rv20`'s annualised volatility in points (for the record's implied-minus-realised line)."""
    variance = daily_realised_variance(closes)
    return None if variance is None else math.sqrt(variance * RV_YEAR) * 100
