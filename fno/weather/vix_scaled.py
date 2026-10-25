"""The first weather model, `weather_vix_v1` (story M1), with zero fitted parameters (design 5.7 rule 5):

- `s_t` = the India VIX close of the regular session before `t`, / 100 / sqrt(252): the daily volatility the market
  priced, known at `t`'s 15:00 cutoff;
- for each of the most recent 750 forecast days `t` whose outcome resolved before the cutoff (at least 500), the
  largest absolute log return of its horizon (`t+1`, or `t+1..t+5`) divided by that day's own `s_t`;
- the probability for day `d` is the share of those standardized moves that, scaled by today's `s_d`, reach 2%.

Today's priced volatility with the tail shape of the last three years, from the data, not an assumed distribution."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date

from ..forecast_v4.terms import BIG_MOVE
from ..forecast_v4_rules.baselines import MINIMUM, MISSING, NOT_ELIGIBLE, WINDOW, Value, before
from .checklist_v0 import Row
from .model import WeatherModel

TRADING_DAYS = 252


@dataclass(frozen=True)
class Standardized:
    resolved_on: date
    largest: float  # the horizon's largest absolute log return over the forecast day's s_t


def daily_scale(vix: float | None) -> float | None:
    return None if vix is None else vix / 100 / math.sqrt(TRADING_DAYS)


class VixScaledWeather(WeatherModel):
    def __init__(self, rows: list[Row]):
        self.days = [r.day for r in rows]
        self.vix = [r.vix for r in rows]
        returns = [abs(math.log(b.close / a.close)) for a, b in zip(rows, rows[1:], strict=False)]
        self.windows = {h: self._standardized(returns, h) for h in (1, 5)}
        self.resolved = {h: [w.resolved_on for w in found] for h, found in self.windows.items()}

    def _standardized(self, returns: list[float], horizon: int) -> list[Standardized]:
        """Forecast day `days[k]` (k >= 1): returns k..k+h-1 (to the next h closes), over the VIX of `days[k-1]`."""
        out = []
        for k in range(1, len(returns) - horizon + 1):
            scale = daily_scale(self.vix[k - 1])
            if scale is not None:
                out.append(Standardized(self.days[k + horizon], max(returns[k : k + horizon]) / scale))
        return out

    def scale(self, d: date) -> float | None:
        i = before(self.days, d) - 1
        return daily_scale(self.vix[i]) if i >= 0 else None  # None: no VIX close for the previous session

    def forecast(self, d: date, horizon: int) -> Value:
        end = before(self.resolved[horizon], d)
        known = self.windows[horizon][max(0, end - WINDOW) : end]
        if len(known) < MINIMUM:
            return Value(NOT_ELIGIBLE)
        scale = self.scale(d)
        if scale is None:
            return Value(MISSING)
        return Value.of(sum(w.largest * scale >= BIG_MOVE for w in known) / len(known), positive=False)
