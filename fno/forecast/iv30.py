"""The 30-day at-the-money implied volatility of a forecast day (story G1; PROTOCOL.md section 3), used by question 5.

Each monthly expiry's ATM IV is B1's (`atm_implied_vol_points`: the mean of the call and put implied volatilities at
the ATM strike, Black-76 on the same-expiry future, traded closes only, `None` on any solver failure). Monthly expiries
are those with a NIFTY future listed that day (story A5's rule). The two monthly expiries bracketing 30 calendar days
(the latest with 1 to 30 days left and the earliest with 30 or more) are interpolated in total variance:

    w_i = iv_i^2 x days_i;   w_30 = w_1 + (w_2 - w_1) x (30 - days_1) / (days_2 - days_1);   iv_30 = sqrt(w_30 / 30)

If 30 days is not bracketed, or either bracketing IV is missing, the monthly expiry with at least 7 days nearest 30
days (a tie goes to the longer one) is used alone, flagged. With none, there is no value.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date

from ..research_data.panel_reader import NiftyPanel
from ..research_engine.features import DecisionContext, Feature, ResearchData
from ..research_engine.implied_vol import ImpliedVolModel
from ..research_engine.volatility_features import atm_implied_vol_points

TARGET_DAYS = 30
FALLBACK_MIN_DAYS = 7
FEATURE_ATM_IV_30D = "G1_atm_iv_30d"


@dataclass(frozen=True)
class AtmIv30:
    points: float  # annualised, in volatility points
    flagged: bool  # True: 30 days was not bracketed, one expiry was used alone
    expiries: tuple[date, ...]  # the expiries used


def interpolate_30d(day: date, atm_ivs: Mapping[date, float | None]) -> AtmIv30 | None:
    """The 30-day ATM IV from each monthly expiry's ATM IV in points (`None` where it is missing)."""
    left = {expiry: (expiry - day).days for expiry in atm_ivs}
    near = [e for e in atm_ivs if 1 <= left[e] <= TARGET_DAYS]
    far = [e for e in atm_ivs if left[e] >= TARGET_DAYS]
    if near and far:
        e1, e2 = max(near), min(far)
        iv1, iv2 = atm_ivs[e1], atm_ivs[e2]
        if iv1 is not None and iv2 is not None:
            return AtmIv30(_interpolated(iv1, left[e1], iv2, left[e2]), False, tuple(sorted({e1, e2})))
    usable = [e for e in atm_ivs if left[e] >= FALLBACK_MIN_DAYS and atm_ivs[e] is not None]
    if not usable:
        return None
    nearest = min(usable, key=lambda e: (abs(left[e] - TARGET_DAYS), -left[e]))
    return AtmIv30(atm_ivs[nearest], True, (nearest,))


def _interpolated(iv1: float, days1: int, iv2: float, days2: int) -> float:
    if days1 == days2:
        return iv1
    w1, w2 = iv1 * iv1 * days1, iv2 * iv2 * days2
    w30 = w1 + (w2 - w1) * (TARGET_DAYS - days1) / (days2 - days1)
    return math.sqrt(w30 / TARGET_DAYS)


class PanelAtmIv30:
    """History: the estimator on the panel's closes of the forecast day (a close proxy for the 15:00 cutoff)."""

    def __init__(self, model: ImpliedVolModel, rate: float):
        self.model, self.rate = model, rate

    def estimate(self, panel: NiftyPanel, day: date) -> AtmIv30 | None:
        session = panel.session_on(day)
        if session is None or session.underlying is None:
            return None
        monthly = {q.expiry for q in panel.futures.get(day, ()) if q.expiry >= day}
        ivs = {e: atm_implied_vol_points(panel, self.model, self.rate, day, e, session.underlying) for e in monthly}
        return interpolate_30d(day, ivs)


class AtmIv30Feature(Feature):
    """The estimate as a feature with its availability (the day's close), so B1's look-ahead harness can test it."""

    name = FEATURE_ATM_IV_30D

    def __init__(self, estimator: PanelAtmIv30):
        self.estimator = estimator

    def value(self, data: ResearchData, decision_day: date, context: DecisionContext) -> float | None:
        estimate = self.estimator.estimate(data.panel, decision_day)
        return None if estimate is None else estimate.points
