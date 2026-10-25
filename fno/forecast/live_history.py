"""The baselines' view on a live forecast day (protocol v2): official closes before the day, the pack's 15:00 values
standing in for the day's own close (`live_1500_proxy`, as B7's live features), and the panel for past days' IV30
(question 5's base rate). The baselines themselves are unchanged (G2); only their inputs come from the pack.

Gates (change 4): the official closes must cover every trading day before the forecast day (`history_stale`
otherwise), and question 5's base rate needs the panel's IV30 history up to the last day whose outcome is known
before the forecast day (`iv30_history_stale` otherwise). A stale history gives "no forecast", never a shorter
window.
"""

from __future__ import annotations

from datetime import date

from ..constants import FORECAST_Q5_RV_BELOW_IV, SESSION_MUHURAT
from ..research_data.calendar import SessionCalendar
from ..research_data.panel_reader import NiftyPanel, SessionClose
from .closes_source import OfficialCloses
from .history import HORIZONS, ForecastHistory
from .iv30 import AtmIv30, PanelAtmIv30
from .live_pack import LivePack
from .targets import trading_days

HISTORY_STALE, IV30_HISTORY_STALE = "history_stale", "iv30_history_stale"


class LiveForecastHistory(ForecastHistory):
    def __init__(self, pack: LivePack, closes: OfficialCloses, panel: NiftyPanel, calendar: SessionCalendar,
                 estimator: PanelAtmIv30):  # fmt: skip
        day = pack.day
        earlier = [SessionClose(d, "regular", n, v) for d, (n, v) in sorted(closes.through(day).items())]
        today = SessionClose(day, "regular", pack.value("nifty_spot"), pack.value("india_vix"))
        past = {d: q for d, q in panel.options.items() if d < day}
        futures = {d: q for d, q in panel.futures.items() if d < day}
        super().__init__(NiftyPanel((*earlier, today), past, futures), calendar, estimator)
        self.pack = pack

    def iv30(self, day: date) -> AtmIv30 | None:
        return self.pack.iv30 if day == self.pack.day else super().iv30(day)

    def near_future(self, day: date) -> tuple[float, date] | None:
        if day != self.pack.day:
            return super().near_future(day)
        iv30 = self.pack.iv30
        if iv30 is None:
            return None
        expiry = iv30.expiries[0]
        price, volume = self.pack.value(f"future_{expiry.isoformat()}"), self._volume(expiry)
        return (price, expiry) if price and volume else None

    def _volume(self, expiry: date) -> int:
        found = next((f for f in self.pack.fields if f.name == f"future_{expiry.isoformat()}_volume"), None)
        return int(found.value) if found is not None else 0


def stale_history(closes: OfficialCloses, calendar: SessionCalendar, day: date) -> list[str]:
    """`history_stale` unless every trading day from the first close to the day before has both official closes."""
    if not closes.rows:
        return [HISTORY_STALE]
    first = min(closes.rows)
    needed = [d for d in trading_days(calendar, first, day) if d < day and calendar.session_kind(d) != SESSION_MUHURAT]
    return [HISTORY_STALE] if closes.missing(needed) else []


def stale_iv30_history(history: ForecastHistory, day: date) -> list[str]:
    """Question 5's base rate needs past IV30 up to the last day whose outcome is known before `day`."""
    last_needed = history.closes.offset(day, -(HORIZONS[FORECAST_Q5_RV_BELOW_IV] + 1))
    known = max(history.panel.options, default=None)
    return [] if last_needed is not None and known is not None and known >= last_needed else [IV30_HISTORY_STALE]
