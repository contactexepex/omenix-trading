"""One G13b record (parts A1-A3): an underlying's issue on a day, from its chain and its official closes, point in
time. Two bases: `CAPTURE` (live and the 3 pm back-fill: `S_ref` is the chain's spot, τ adds the rest of the day, only
closes before the day are read) and `CLOSE` (the end-of-day back-fill: `S_ref` is the day's close, τ = k, closes up to
and including the day)."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from ..forecast_v4_rules.series import DayValue
from ..price_distribution.chain import ChainDay, QuoteFilter, SpreadFilter, TradedCloseFilter
from ..price_distribution.constants import SOURCE_PANEL
from ..price_distribution.horizons import nth_regular_session, previous_regular_session, regular_sessions_until
from ..price_distribution.valuation import value_day
from ..research_data.calendar import CalendarError, SessionCalendar
from .bhavcopy_chains import SOURCE_BHAVCOPY
from .constants import (
    HORIZON_SESSIONS,
    HORIZONS_AT,
    METHOD_VERSION,
    MISSING,
    NOT_ELIGIBLE,
    OK,
    REST_OF_DAY,
    SCHEMA,
)
from .forecasters import RULE_RANGES, RangeForecast, RangeForecaster, RangeInputs
from .records import check_header, range_row

CALENDAR_ENDS = "the session calendar ends before the target ({error})"
NO_REFERENCE = "no reference price: {why}"
STALE = "closes stale: the last close read is {last}, the method needs {expected}"
PROBLEMS = "problems"


@dataclass(frozen=True)
class Basis:
    name: str
    tail: float
    reads_day_close: bool  # True: the day's own close is known (end of day)


CAPTURE, CLOSE = Basis("capture", REST_OF_DAY, False), Basis("close", 0.0, True)


def missing_issue(underlying: str, day: date, issue: str, label: str, reason: str, method: str,
                  issued_at: str | None) -> dict:  # fmt: skip
    """An issue that could not be built, on file so the gap is recorded (owner, 16 Oct)."""
    check_header(issue, label)
    return {"schema": SCHEMA, "underlying": underlying, "day": day.isoformat(), "issue": issue, "label": label,
            "issued_at": issued_at, "method_version": METHOD_VERSION, "method_sha256": method, "status": MISSING,
            "problems": [reason], "rows": []}  # fmt: skip


def quote_filter(source: str) -> QuoteFilter:
    """End-of-day prices (G13's panel, the bhavcopy) are traded closes; 3 pm quotes are two-sided."""
    return TradedCloseFilter() if source in (SOURCE_PANEL, SOURCE_BHAVCOPY) else SpreadFilter()


class RangeBuilder:
    def __init__(self, calendar: SessionCalendar, rate: float, method_sha256: str,
                 forecasters: Sequence[RangeForecaster] | None = None):  # fmt: skip
        self.calendar, self.rate, self.method = calendar, rate, method_sha256
        self.forecasters = tuple(forecasters or (cls() for cls in RULE_RANGES))

    def build(self, underlying: str, day: date, issue: str, chain: ChainDay | None, closes: Sequence[DayValue],
              basis: Basis, label: str, issued_at: str | None) -> dict:  # fmt: skip
        check_header(issue, label)  # an unknown issue is refused, never a bare KeyError (judge 416)
        read = tuple(c for c in closes if c.day < day or (basis.reads_day_close and c.day == day))
        s_ref, s_ref_at, why = self._reference(day, chain, read, basis)
        if s_ref is None:
            return missing_issue(underlying, day, issue, label, NO_REFERENCE.format(why=why), self.method, issued_at)
        valuation = value_day(chain, quote_filter(chain.source), self.rate) if chain is not None else None  # G13's
        expiries = [e.expiry for e in valuation.expiries] if valuation else []
        to_expiry = {e: self._sessions(day, e) for e in expiries}
        inputs = RangeInputs(day, s_ref, basis.tail, read, valuation, {e: n for e, n in to_expiry.items() if n})
        stale = self._stale(day, read, basis)
        rows = [self._row(f, h, day, inputs, stale) for h in HORIZONS_AT[issue] for f in self.forecasters]
        problems = [f"{r['forecaster']} {r['horizon']}: {r['reason']}" for r in rows if r["status"] == MISSING]
        return {"schema": SCHEMA, "underlying": underlying, "day": day.isoformat(), "issue": issue, "label": label,
                "issued_at": issued_at, "method_version": METHOD_VERSION, "method_sha256": self.method,
                "inputs_sha256": self._inputs_sha256(chain, read), "basis": basis.name, "s_ref": s_ref,
                "s_ref_at": s_ref_at, "chain": chain.snapshot_id if chain else None,
                "chain_source": chain.source if chain else None, "closes_through": read[-1].day.isoformat()
                if read else None, "status": PROBLEMS if problems else OK, "problems": problems,
                "rows": rows}  # fmt: skip

    def _reference(self, day: date, chain: ChainDay | None, read: tuple[DayValue, ...], basis: Basis):
        if basis.reads_day_close:
            if read and read[-1].day == day:
                return read[-1].value, f"{day.isoformat()}T15:30:00+05:30", None
            return None, None, f"no official close of {day}"
        if chain is None or chain.spot is None:
            return None, None, "no 3 pm chain with a spot"
        return chain.spot, chain.observed_at, None

    def _stale(self, day: date, read: tuple[DayValue, ...], basis: Basis) -> str | None:
        try:
            expected = day if basis.reads_day_close else previous_regular_session(self.calendar, day)
        except CalendarError as error:
            return STALE.format(last=read[-1].day if read else None, expected=f"a session the calendar knows ({error})")
        last = read[-1].day if read else None
        return None if last == expected else STALE.format(last=last, expected=expected)

    def _row(self, forecaster: RangeForecaster, horizon: str, day: date, inputs: RangeInputs,
             stale: str | None) -> dict:  # fmt: skip
        k = HORIZON_SESSIONS[horizon]
        try:
            target = nth_regular_session(self.calendar, day, k)
        except CalendarError as error:
            return range_row(forecaster.name, horizon, None, None, inputs.s_ref,
                             RangeForecast(NOT_ELIGIBLE, CALENDAR_ENDS.format(error=error)))  # fmt: skip
        found = RangeForecast(MISSING, stale) if stale and forecaster.reads_closes else forecaster.forecast(inputs, k)
        return range_row(forecaster.name, horizon, target, k + inputs.tail, inputs.s_ref, found)

    def _sessions(self, day: date, expiry: date) -> int | None:
        if expiry <= day:
            return None
        try:
            return regular_sessions_until(self.calendar, day, expiry)
        except CalendarError:
            return None

    def _inputs_sha256(self, chain: ChainDay | None, read: tuple[DayValue, ...]) -> str:
        closes = [[c.day.isoformat(), c.value] for c in read]  # all of them: G7's Ewma reads from the first
        payload = [chain.inputs_sha256 if chain else None, closes, self.calendar.calendar_sha256(), self.rate]
        return hashlib.sha256(json.dumps(payload).encode()).hexdigest()
