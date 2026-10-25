"""G13b's range forecasters (part A2), each the log return `ln(close at target / S_ref)` at the five levels and P(up):
`implied` from G13's distribution of the day's chain, `rv20`, `hist750`, `ewma_t4` (G7's `Ewma`, imported) and the
`no_change` point mass. τ is the target's sessions plus the rest of the day after the capture (`RangeInputs.tail`)."""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from statistics import NormalDist

import numpy as np

from ..forecast_v4_rules.baselines import Ewma
from ..forecast_v4_rules.series import DayValue, close_proxy_rv
from ..price_distribution.constants import HIST_MINIMUM, HIST_WINDOW, RV_WINDOW
from ..price_distribution.forecasters import daily_realised_variance, log_returns
from ..price_distribution.valuation import DayValuation
from .constants import (
    EWMA_T4,
    HIST750,
    IMPLIED,
    LEVELS,
    MISSING,
    NO_CHANGE,
    NOT_ELIGIBLE,
    OK,
    RV20,
)
from .t4 import t4_quantile

Z = [NormalDist().inv_cdf(level) for level in LEVELS]
T4 = [t4_quantile(level) / math.sqrt(2) for level in LEVELS]  # unit variance: t(4) has variance 2
BIG_MOVE = 0.02  # G7's consistency line: P(|log r| >= 0.02), as V6a, reported beside it and never scored
NO_EXPIRY = "no expiry with a distribution and at least {k} sessions after the day"
TOO_FEW_CLOSES = "{n} closes ({minimum} needed)"
TOO_FEW_RETURNS = "{n} {k}-session returns in the last {window} closes ({minimum} needed)"
NO_EWMA = "no EWMA variance before the day (G7's Ewma needs 250 sessions)"
NOT_INCREASING = "quantiles not strictly increasing"


@dataclass(frozen=True)
class RangeInputs:
    day: date
    s_ref: float
    tail: float  # sessions of variance left in the day after the capture (0 at the close)
    closes: tuple[DayValue, ...]  # the official closes the method may read, in date order
    valuation: DayValuation | None = None
    sessions_to_expiry: dict[date, int] = field(default_factory=dict)


@dataclass(frozen=True)
class RangeForecast:
    status: str
    reason: str | None = None
    log_quantiles: tuple[float, ...] | None = None
    p_up: float | None = None
    p_big_move: float | None = None  # implied only


def increasing(values, p_up, p_big=None, equal_allowed=False) -> RangeForecast:
    values = tuple(float(v) for v in values)
    pairs = list(zip(values, values[1:], strict=False))
    if not equal_allowed and any(b <= a for a, b in pairs):
        return RangeForecast(MISSING, NOT_INCREASING)
    return RangeForecast(OK, None, values, p_up, p_big)


class RangeForecaster(ABC):
    name: str
    reads_closes = False  # True: its closes must reach the previous regular session

    @abstractmethod
    def forecast(self, inputs: RangeInputs, k: int) -> RangeForecast:
        """The range of `ln(close k sessions after the day / S_ref)`."""


class ImpliedRange(RangeForecaster):
    """The shortest expiry with `n >= k` sessions after the day, re-centred and scaled as G13's `h1`/`h5`: centring by
    `share = τ / (n + tail)`, spread around the median by `sqrt(share)`."""

    name = IMPLIED

    def forecast(self, inputs: RangeInputs, k: int) -> RangeForecast:
        usable = inputs.valuation.usable() if inputs.valuation is not None else []
        for expiry in usable:
            n = inputs.sessions_to_expiry.get(expiry.expiry)
            if n is not None and n >= k:
                return self._scaled(inputs, expiry, (k + inputs.tail) / (n + inputs.tail))
        return RangeForecast(MISSING, NO_EXPIRY.format(k=k))

    @staticmethod
    def _scaled(inputs: RangeInputs, expiry, share: float) -> RangeForecast:
        found, forward = expiry.distribution.distribution, expiry.forward
        median = math.log(found.quantile(0.5)[0] / forward)
        centre = share * (math.log(forward / inputs.s_ref) + median)
        root = math.sqrt(share)
        values = [centre + root * (math.log(found.quantile(t)[0] / forward) - median) for t in LEVELS]

        def cdf(y: float) -> float:  # P(log return <= y) on the scaled distribution
            return found.cdf(forward * math.exp(median + (y - centre) / root))

        p_big = cdf(-BIG_MOVE) + 1 - cdf(BIG_MOVE)
        return increasing(values, 1 - cdf(0.0), p_big)


class RealisedVolRange(RangeForecaster):
    """Lognormal, zero log drift, at B1's realised volatility of the last 20 closes, over τ."""

    name = RV20
    reads_closes = True

    def forecast(self, inputs: RangeInputs, k: int) -> RangeForecast:
        variance = daily_realised_variance(inputs.closes)  # G13's rv20 rule, imported
        if variance is None:
            return RangeForecast(NOT_ELIGIBLE, TOO_FEW_CLOSES.format(n=len(inputs.closes), minimum=RV_WINDOW + 1))
        return increasing([z * math.sqrt(variance) * math.sqrt(k + inputs.tail) for z in Z], 0.5)


class HistoricalRange(RangeForecaster):
    """The empirical quantiles (numpy's linear rule) of every k-session log return in the last 750 closes."""

    name = HIST750
    reads_closes = True

    def forecast(self, inputs: RangeInputs, k: int) -> RangeForecast:
        window = inputs.closes[-HIST_WINDOW:]
        returns = log_returns(window, k)
        if len(returns) < HIST_MINIMUM:
            reason = TOO_FEW_RETURNS.format(n=len(returns), k=k, window=HIST_WINDOW, minimum=HIST_MINIMUM)
            return RangeForecast(NOT_ELIGIBLE, reason)
        up = sum(1 for r in returns if r > 0) / len(returns)
        return increasing(np.quantile(np.array(returns), LEVELS), up)


class EwmaT4Range(RangeForecaster):
    """`s T / sqrt(2)` with `T ~ t(4)` and `s^2` G7's EWMA one-session variance at the day, over τ (G7's builder)."""

    name = EWMA_T4
    reads_closes = True

    def forecast(self, inputs: RangeInputs, k: int) -> RangeForecast:
        rv = close_proxy_rv(list(inputs.closes))
        s2 = Ewma(rv).variance(_after(inputs.closes[-1].day)) if inputs.closes else None
        if s2 is None:
            return RangeForecast(NOT_ELIGIBLE, NO_EWMA)
        return increasing([t * math.sqrt(s2 * (k + inputs.tail)) for t in T4], 0.5)


def _after(day: date) -> date:
    """A date after the last close read, so `Ewma.variance` (the last session before it) includes that close."""
    return date.fromordinal(day.toordinal() + 1)


class NoChangeRange(RangeForecaster):
    """A point mass at `S_ref`: all five quantiles at zero log return and P(up) = 0.5."""

    name = NO_CHANGE

    def forecast(self, inputs: RangeInputs, k: int) -> RangeForecast:
        return increasing([0.0] * len(LEVELS), 0.5, equal_allowed=True)


RULE_RANGES = (ImpliedRange, RealisedVolRange, HistoricalRange, EwmaT4Range, NoChangeRange)
