"""What the baselines may read on a forecast day, from the NIFTY panel (story G2; PROTOCOL.md sections 1 and 4).

History inputs are the close proxy: `d`'s own close stands for its 15:00 values (labelled "close proxy"). Every
question's outcome is computed once, with the trading day on which it became known (its last close); a baseline on
`d` may use an outcome only if that day is before `d`. Nothing else after `d` is read: IV30, the near future and the
regressors of `d` use `d` and earlier only. B1's look-ahead harness checks this on real days
(`tests/forecast/test_baselines_lookahead.py`).
"""

from __future__ import annotations

from datetime import date, timedelta

from ..constants import (
    FORECAST_Q1_UP_20D,
    FORECAST_Q2_MOVE_3PCT_20D,
    FORECAST_Q3_RV_RISES_20D,
    FORECAST_Q4_VIX_UP_10D,
    FORECAST_Q5_RV_BELOW_IV,
)
from ..research_data.calendar import CalendarError, SessionCalendar
from ..research_data.panel_reader import NiftyPanel
from .iv30 import AtmIv30, PanelAtmIv30
from .targets import PRICE_HORIZON, VIX_HORIZON, ForecastTargets, daily_closes, trading_days

HORIZONS = {
    FORECAST_Q1_UP_20D: PRICE_HORIZON,
    FORECAST_Q2_MOVE_3PCT_20D: PRICE_HORIZON,
    FORECAST_Q3_RV_RISES_20D: PRICE_HORIZON,
    FORECAST_Q4_VIX_UP_10D: VIX_HORIZON,
    FORECAST_Q5_RV_BELOW_IV: PRICE_HORIZON,
}
CALENDAR_LOOKAHEAD_DAYS = 45  # calendar days that always hold 20 trading days (the calendar is published ahead)


class ForecastHistory:
    def __init__(self, panel: NiftyPanel, calendar: SessionCalendar, estimator: PanelAtmIv30):
        self.panel, self.calendar, self.estimator = panel, calendar, estimator
        dated = [s for s in panel.sessions if s.underlying is not None]
        last = max(s.day for s in panel.sessions)  # the forecast day even when its own close is missing
        self.closes = daily_closes(calendar, dated[0].day, last, panel.sessions)
        self.targets = ForecastTargets(self.closes)
        self.days = self.closes.days
        self.index = {day: i for i, day in enumerate(self.days)}
        self._iv30: dict[date, AtmIv30 | None] = {}
        self._outcomes: dict[tuple[str, date], tuple[bool | None, date | None]] = {}

    def iv30(self, day: date) -> AtmIv30 | None:
        if day not in self._iv30:
            self._iv30[day] = self.estimator.estimate(self.panel, day) if day in self.panel.options else None
        return self._iv30[day]

    def near_future(self, day: date) -> tuple[float, date] | None:
        """The traded close and expiry of the first expiry IV30 used on `day` (the risk-neutral carry)."""
        iv30, spot = self.iv30(day), self.closes.nifty.get(day)
        if iv30 is None or spot is None:
            return None
        expiry = iv30.expiries[0]
        price = self.estimator.model.underlying(spot, self.panel.future_on(day, expiry))
        return None if price is None else (price, expiry)

    def outcome(self, question: str, day: date) -> tuple[bool | None, date | None]:
        """The question's outcome for forecast day `day` and the trading day it became known (None: never)."""
        key = (question, day)
        if key not in self._outcomes:
            known_on = self.closes.offset(day, HORIZONS[question])
            self._outcomes[key] = (self.targets.outcome(question, day, self.iv30(day)), known_on)
        return self._outcomes[key]

    def earlier(self, day: date) -> list[date]:
        """Trading days before `day`, newest first."""
        i = self.index.get(day, 0)
        return self.days[:i][::-1]

    def resolved_before(self, question: str, day: date, window: int) -> list[tuple[date, bool]]:
        """The most recent `window` earlier days whose outcome was known before `day` and is not void, newest first."""
        found = []
        for t in self.earlier(day):
            value, known_on = self.outcome(question, t)
            if value is not None and known_on is not None and known_on < day:
                found.append((t, value))
                if len(found) == window:
                    break
        return found

    def horizon_day(self, day: date, sessions: int) -> date | None:
        """The calendar's `sessions`-th trading day after `day` (known in advance; None beyond the calendar)."""
        try:
            ahead = trading_days(self.calendar, day + timedelta(days=1), day + timedelta(days=CALENDAR_LOOKAHEAD_DAYS))
        except CalendarError:
            return None
        return ahead[sessions - 1] if len(ahead) >= sessions else None
