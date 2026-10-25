"""F1 and F2 (story B1): volatility features on daily closes."""

from __future__ import annotations

from datetime import date
from statistics import median

from ..constants import FEATURE_ATM_IV_MINUS_RV20, FEATURE_VIX_ABOVE_MEDIAN, OPTION_CALL, OPTION_PUT
from ..research_data.panel_reader import NiftyPanel, OptionQuote
from .close_series import daily_sessions, last_valid, realised_vol_points
from .features import DecisionContext, Feature, ResearchData
from .implied_vol import ImpliedVolModel, OptionPricing

REALISED_RETURNS = 20  # F1: past 20 daily log returns (21 closes)
VIX_HISTORY = 250  # F2: previous 250 valid India VIX closes
DAYS_PER_YEAR = 365  # option time: calendar days to expiry / 365
TRADED = 1  # contracts: a leg that traded at all
F1_MIN_LEG_VOLUME = 10  # protocol v2.2: the thinner ATM leg must have traded at least 10 contracts (owner, 13 Oct 2026)


def atm_strike(quotes: list[OptionQuote], spot: float) -> float | None:
    """The listed strike nearest the spot close; on an equal-distance tie the lower strike."""
    strikes = {q.strike for q in quotes}
    return min(strikes, key=lambda k: (abs(k - spot), k)) if strikes else None


def traded_close(quotes: list[OptionQuote], strike: float, kind: str, min_volume: int = TRADED) -> float | None:
    """The leg's close if it traded at least `min_volume` contracts that day; settlement is never used for features."""
    leg = next((q for q in quotes if q.strike == strike and q.kind == kind), None)
    return leg.close if leg is not None and leg.volume >= min_volume and leg.close > 0 else None


def atm_implied_vol_points(
    panel: NiftyPanel,
    model: ImpliedVolModel,
    rate: float,
    day: date,
    expiry: date,
    spot: float,
    min_volume: int = TRADED,
) -> float | None:
    """One expiry's ATM implied volatility on `day`, in points: the mean of the call and put IVs at the ATM strike, both
    legs traded (at least `min_volume` contracts each), priced on the model's underlying (B1). `None` when a leg, the
    underlying or a solution is missing."""
    quotes = panel.options_on(day, expiry)
    strike = atm_strike(quotes, spot)
    underlying = model.underlying(spot, panel.future_on(day, expiry))
    if strike is None or underlying is None:
        return None
    years = (expiry - day).days / DAYS_PER_YEAR
    vols = []
    for kind in (OPTION_CALL, OPTION_PUT):
        price = traded_close(quotes, strike, kind, min_volume)
        if price is None:
            return None
        vol = model.implied_vol(OptionPricing(price, underlying, strike, kind, years, rate))
        if vol is None:
            return None
        vols.append(vol)
    return sum(vols) / len(vols) * 100


class AtmIvMinusRealised(Feature):
    """F1: ATM implied volatility (mean of the call and put IVs at the ATM strike of the cycle's expiry) minus the
    realised volatility of the past 20 daily log returns, both in volatility points. Needs both legs, each with at least
    10 contracts traded (the thinner leg's volume decides; below it F1 is `None`, never a settlement price)."""

    name = FEATURE_ATM_IV_MINUS_RV20

    def __init__(self, model: ImpliedVolModel, rate: float):
        self.model, self.rate = model, rate

    def value(self, data: ResearchData, decision_day: date, context: DecisionContext) -> float | None:
        sessions = daily_sessions(data.panel, decision_day)
        if not sessions or sessions[-1].day != decision_day or sessions[-1].underlying is None:
            return None  # not a daily session, or the panel left it out
        implied = self.atm_implied_vol_points(data, decision_day, context.expiry, sessions[-1].underlying)
        realised = realised_vol_points([s.underlying for s in sessions], REALISED_RETURNS)
        return None if implied is None or realised is None else implied - realised

    def atm_implied_vol_points(self, data: ResearchData, day: date, expiry: date, spot: float) -> float | None:
        return atm_implied_vol_points(data.panel, self.model, self.rate, day, expiry, spot, F1_MIN_LEG_VOLUME)


class VixAboveMedian(Feature):
    """F2: the decision day's India VIX close is above the median of the previous 250 valid closes (the decision day
    excluded)."""

    name = FEATURE_VIX_ABOVE_MEDIAN

    def value(self, data: ResearchData, decision_day: date, context: DecisionContext) -> bool | None:
        sessions = daily_sessions(data.panel, decision_day)
        if not sessions or sessions[-1].day != decision_day or sessions[-1].vix is None:
            return None
        history = last_valid(sessions[:-1], lambda s: s.vix, VIX_HISTORY)
        if len(history) < VIX_HISTORY:
            return None
        return sessions[-1].vix > median(history)
