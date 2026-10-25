"""Live 15:00 versions of F1-F3 (story B7): the same `Feature` interface, known at the desk's decision time, computed
only from what the desk has then.

Inputs at the cutoff: the canonical A4 snapshot of the day, used only if its capture finished by the cutoff (a later
capture is data after the cutoff); its spot, its valid two-sided option quotes (mids, never the last price), India VIX
and the NIFTY futures recorded during the capture; closes from the panel up to the previous session.
- Live F1: ATM strike = the snapshot's strike nearest spot (lower on a tie); the IV model's underlying from the
  recorded same-expiry future (Black-76, as research F1; a future that has not traded today gives None); the call and
  put IVs of the mids, averaged. Realised volatility: the last 20 log returns of the previous 20 sessions' closes
  followed by the 15:00 spot.
- Live F2: VIX at the cutoff above the median of the previous 250 valid closes.
- Live F3: F3 itself (events are dated by announcement day), declared at the cutoff.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from statistics import median

from ..constants import (
    FEATURE_ATM_IV_MINUS_RV20_LIVE,
    FEATURE_EVENT_IN_WINDOW_LIVE,
    FEATURE_VIX_ABOVE_MEDIAN_LIVE,
    OPTION_CALL,
    OPTION_PUT,
)
from ..research_data.quote_snapshots import CutoffSnapshot, LiveQuote
from .close_series import daily_sessions, last_valid, realised_vol_points
from .event_features import ScheduledEventInWindow
from .features import DecisionContext, Feature, ResearchData
from .implied_vol import ImpliedVolModel, OptionPricing
from .volatility_features import DAYS_PER_YEAR, REALISED_RETURNS, VIX_HISTORY


class LiveFeature(Feature):
    """Known at the desk's decision time on the decision day."""

    def __init__(self, cutoff: time):
        self.cutoff = cutoff

    def known_at(self, decision_day: date) -> datetime:
        return datetime.combine(decision_day, self.cutoff)

    def snapshot(self, data: ResearchData, day: date) -> CutoffSnapshot | None:
        """The day's snapshot if its capture finished by the cutoff."""
        found = data.snapshots.get(day)
        return found if found is not None and found.finished_at <= self.known_at(day) else None


def _mid(quotes: list[LiveQuote], strike: float, kind: str) -> float | None:
    leg = next((q for q in quotes if q.strike == strike and q.kind == kind), None)
    return leg.mid if leg is not None else None


class LiveAtmIvMinusRealised(LiveFeature):
    name = FEATURE_ATM_IV_MINUS_RV20_LIVE

    def __init__(self, cutoff: time, rate: float, model: ImpliedVolModel):
        super().__init__(cutoff)
        self.rate, self.model = rate, model

    def value(self, data: ResearchData, decision_day: date, context: DecisionContext) -> float | None:
        snapshot = self.snapshot(data, decision_day)
        if snapshot is None or snapshot.spot is None or snapshot.spot <= 0:
            return None
        implied = self.atm_implied_vol_points(snapshot, context.expiry)
        closes = [s.underlying for s in daily_sessions(data.panel, decision_day - timedelta(days=1))]
        realised = realised_vol_points([*closes, snapshot.spot], REALISED_RETURNS)
        return None if implied is None or realised is None else implied - realised

    def atm_implied_vol_points(self, snapshot: CutoffSnapshot, expiry: date) -> float | None:
        quotes = snapshot.quotes_for(expiry)
        strikes = {q.strike for q in quotes}
        underlying = self.model.underlying(snapshot.spot, snapshot.future_for(expiry))
        years = (expiry - snapshot.day).days / DAYS_PER_YEAR
        if not strikes or underlying is None or years <= 0:
            return None
        strike = min(strikes, key=lambda k: (abs(k - snapshot.spot), k))
        vols = []
        for kind in (OPTION_CALL, OPTION_PUT):
            price = _mid(quotes, strike, kind)
            vol = (
                None
                if price is None
                else self.model.implied_vol(OptionPricing(price, underlying, strike, kind, years, self.rate))
            )
            if vol is None:
                return None
            vols.append(vol)
        return sum(vols) / len(vols) * 100


class LiveVixAboveMedian(LiveFeature):
    name = FEATURE_VIX_ABOVE_MEDIAN_LIVE

    def value(self, data: ResearchData, decision_day: date, context: DecisionContext) -> bool | None:
        snapshot = self.snapshot(data, decision_day)
        if snapshot is None or snapshot.vix is None:
            return None
        history = last_valid(daily_sessions(data.panel, decision_day - timedelta(days=1)), lambda s: s.vix, VIX_HISTORY)
        return snapshot.vix > median(history) if len(history) == VIX_HISTORY else None


class LiveScheduledEventInWindow(LiveFeature):
    name = FEATURE_EVENT_IN_WINDOW_LIVE

    def value(self, data: ResearchData, decision_day: date, context: DecisionContext) -> bool:
        return ScheduledEventInWindow().value(data, decision_day, context)
