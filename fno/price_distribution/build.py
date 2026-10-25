"""One underlying's day record (sections 2-4): the chain's valuation and, for NIFTY, every rule forecaster at every
horizon. Point in time: only that day's chain and the closes strictly before the day are read."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from datetime import date

from ..constants import NIFTY_SYMBOL
from ..forecast_v4_rules.series import DayValue
from ..research_data.calendar import SessionCalendar
from .chain import ChainDay, QuoteFilter, SpreadFilter, TradedCloseFilter
from .constants import HIST_WINDOW, HORIZONS, METHOD_VERSION, MISSING, OK, RISK_NEUTRAL_NOTE, SOURCE_PANEL
from .forecasters import (
    Forecast,
    ForecastInputs,
    HistoricalForecaster,
    ImpliedForecaster,
    QuantileForecaster,
    RealisedVolForecaster,
    realised_vol_points,
)
from .horizons import previous_regular_session, targets
from .records import RATE_SOURCE, SCHEMA, Stamp, forecast_row, valuation_dict
from .valuation import value_day

NO_SPOT = "no spot in the chain"
STALE_CLOSES = "closes stale: the last close before the day is {last}, the previous regular session is {expected}"
PROBLEMS = "problems"


def quote_filter(source: str) -> QuoteFilter:
    return TradedCloseFilter() if source == SOURCE_PANEL else SpreadFilter()


def missing_record(underlying: str, day: date, reason: str, stamp: Stamp) -> dict:
    """The record of a day whose chain could not be used: written, so the gap is on file (owner, 16 Oct)."""
    return {"schema": SCHEMA, "underlying": underlying, "day": day.isoformat(), "label": stamp.label,
            "made_at": stamp.made_at, "method_version": METHOD_VERSION, "method_sha256": stamp.method_sha256,
            "status": MISSING, "problems": [reason], "valuation": None, "forecasts": []}  # fmt: skip


class DayBuilder:
    def __init__(self, calendar: SessionCalendar, rate: float, closes: Sequence[DayValue], method_sha256: str,
                 forecasters: Sequence[QuantileForecaster] | None = None):  # fmt: skip
        self.calendar, self.rate, self.closes, self.method = calendar, rate, tuple(closes), method_sha256
        self.forecasters = tuple(forecasters or (ImpliedForecaster(), RealisedVolForecaster(), HistoricalForecaster()))

    def build(self, chain: ChainDay, label: str, made_at: str | None) -> dict:
        before = tuple(c for c in self.closes if c.day < chain.day)
        stamp = Stamp(label, self.method, self._inputs_sha256(chain, before), made_at)
        valuation = value_day(chain, quote_filter(chain.source), self.rate)
        nifty = chain.underlying == NIFTY_SYMBOL
        rows = self._forecasts(chain, valuation, before, stamp) if nifty else []
        problems = valuation.problems + [f"{r['forecaster']} {r['horizon']}: {r['reason']}" for r in rows
                                         if r["status"] == MISSING]  # fmt: skip
        return {"schema": SCHEMA, "underlying": chain.underlying, "day": chain.day.isoformat(), "label": label,
                "made_at": made_at, "method_version": METHOD_VERSION, "method_sha256": self.method,
                "inputs_sha256": stamp.inputs_sha256, "source": chain.source, "snapshot_id": chain.snapshot_id,
                "chain_sha256": chain.inputs_sha256, "observed_at": chain.observed_at, "spot": chain.spot,
                "source_note": chain.source_note,
                "rate": self.rate, "rate_source": RATE_SOURCE, "note": RISK_NEUTRAL_NOTE,
                "status": PROBLEMS if problems else OK, "problems": problems,
                "valuation": valuation_dict(valuation, realised_vol_points(before) if nifty else None),
                "forecasts": rows}  # fmt: skip

    def _forecasts(self, chain: ChainDay, valuation, before: tuple[DayValue, ...], stamp: Stamp) -> list[dict]:
        found = targets(self.calendar, chain.day, [e.expiry for e in valuation.expiries])
        to_expiry = {t.expiry: t.sessions for t in found.values() if t.expiry is not None and t.sessions}
        stale = self._stale(chain.day, before)
        rows = []
        for forecaster in self.forecasters:
            for horizon in HORIZONS:
                target = found[horizon]
                if chain.spot is None:
                    forecast = Forecast(MISSING, NO_SPOT)
                elif stale and forecaster.reads_closes:
                    forecast = Forecast(MISSING, stale)
                else:
                    inputs = ForecastInputs(chain.day, chain.spot, valuation, before, to_expiry)
                    forecast = forecaster.forecast(inputs, target)
                rows.append(forecast_row(chain.day, forecaster.name, target, chain.spot, forecast, stamp))
        return rows

    def _stale(self, day: date, before: tuple[DayValue, ...]) -> str | None:
        """Why the closes cannot be trusted for the day: they must reach the previous regular session."""
        expected = previous_regular_session(self.calendar, day)
        last = before[-1].day if before else None
        return None if last == expected else STALE_CLOSES.format(last=last, expected=expected)

    def _inputs_sha256(self, chain: ChainDay, before: tuple[DayValue, ...]) -> str:
        closes = [[c.day.isoformat(), c.value] for c in before[-(HIST_WINDOW + 1) :]]  # all a forecaster reads
        payload = json.dumps([chain.inputs_sha256, closes, self.calendar.calendar_sha256(), self.rate])
        return hashlib.sha256(payload.encode()).hexdigest()
