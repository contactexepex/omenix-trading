"""Baselines (a) and (b) of the frozen forecast protocol (story G2; PROTOCOL.md section 4), point-in-time.

(a) **Risk-neutral, questions 1 and 2 only**, labelled risk-neutral (option prices include risk premia; not a
real-world probability). `ln(S_T/S_0)` is normal with mean `m = c tau - s^2 tau / 2` and variance `s^2 tau`:
`S_0` NIFTY at the cutoff, `s` = IV30 / 100 (a flagged IV30 is used and its flag carried), `tau` = calendar days from
`d` to `d+20` / 365, carry `c = ln(F_1 / S_0) / tau_1` from the traded close of the first expiry IV30 used.
(b) **Base rate, every question**: the share of 1s among the most recent 750 earlier days whose outcome was known
before `d` and is not void; at least 500, else no forecast.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date

from ..analytics import norm_cdf
from ..constants import (
    BASELINE_BASE_RATE,
    BASELINE_RISK_NEUTRAL,
    FORECAST_Q1_UP_20D,
    FORECAST_Q2_MOVE_3PCT_20D,
    FORECAST_QUESTIONS,
)
from .history import ForecastHistory
from .targets import MOVE_THRESHOLD, PRICE_HORIZON

DAYS_PER_YEAR = 365.0
BASE_RATE_WINDOW, BASE_RATE_MINIMUM = 750, 500
RISK_NEUTRAL_LABEL = "risk-neutral: option prices include risk premia; not a real-world probability"

Probabilities = dict[str, float | None]


@dataclass(frozen=True)
class LognormalInputs:
    spot: float
    sigma: float  # annualised, a fraction
    tau: float  # years to the target day
    carry: float  # annualised log carry of the near future


def lognormal_probabilities(x: LognormalInputs) -> tuple[float, float]:
    """(Q1, Q2) under the lognormal: P(S_T > S_0) and P(|S_T / S_0 - 1| >= 3%)."""
    spread = x.sigma * math.sqrt(x.tau)
    mean = x.carry * x.tau - x.sigma * x.sigma * x.tau / 2
    up = norm_cdf(mean / spread)
    move = 1 - norm_cdf((math.log(1 + MOVE_THRESHOLD) - mean) / spread)
    move += norm_cdf((math.log(1 - MOVE_THRESHOLD) - mean) / spread)
    return up, move


class RiskNeutralBaseline:
    name = BASELINE_RISK_NEUTRAL

    def __init__(self, history: ForecastHistory):
        self.history = history

    def inputs(self, day: date) -> LognormalInputs | None:
        h = self.history
        spot, iv30, near = h.closes.nifty.get(day), h.iv30(day), h.near_future(day)
        target = h.horizon_day(day, PRICE_HORIZON)
        if spot is None or iv30 is None or near is None or target is None:
            return None
        future, expiry = near
        tau, tau_1 = (target - day).days / DAYS_PER_YEAR, (expiry - day).days / DAYS_PER_YEAR
        if tau_1 <= 0:
            return None
        return LognormalInputs(spot, iv30.points / 100, tau, math.log(future / spot) / tau_1)

    def probabilities(self, day: date) -> Probabilities:
        out: Probabilities = dict.fromkeys(FORECAST_QUESTIONS)
        x = self.inputs(day)
        if x is not None:
            out[FORECAST_Q1_UP_20D], out[FORECAST_Q2_MOVE_3PCT_20D] = lognormal_probabilities(x)
        return out

    def flagged(self, day: date) -> bool | None:
        """The IV30 flag the risk-neutral values carry (reported split by it, protocol section 7)."""
        iv30 = self.history.iv30(day)
        return None if iv30 is None else iv30.flagged


class BaseRateBaseline:
    name = BASELINE_BASE_RATE

    def __init__(self, history: ForecastHistory, window: int = BASE_RATE_WINDOW, minimum: int = BASE_RATE_MINIMUM):
        self.history, self.window, self.minimum = history, window, minimum

    def probability(self, question: str, day: date) -> float | None:
        resolved = self.history.resolved_before(question, day, self.window)
        if len(resolved) < self.minimum:
            return None
        return sum(value for _, value in resolved) / len(resolved)

    def probabilities(self, day: date) -> Probabilities:
        return {q: self.probability(q, day) for q in FORECAST_QUESTIONS}
