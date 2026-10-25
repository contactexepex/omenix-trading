"""One session's five G14 rows (story G14, "The forecasters"): v4's own forecasters and capture (G7,
`fno/forecast_v4_rules/capture.py`), imported unchanged, run on the spliced series in place of A16's live rows. v4's
`capture_day` keeps its refusals (today only, a scored session, before 14:30 IST); of its rows only V1's five are kept,
renamed and written with G14's columns."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import date, datetime

from ..constants import (
    V1_RV_1S,
    V4_BASELINE_EWMA,
    V4_BASELINE_HAR_DAILY,
    V4_BASELINE_HAR_INTRADAY,
    V4_BASELINE_TRAILING,
    V4_RULE_V1_CLOSE_BLEND,
)
from ..forecast_v4_rules.baselines import before
from ..forecast_v4_rules.capture import DayForecasts, Inputs, capture_day, cutoff
from ..forecast_v4_rules.records import Record
from ..forecast_v4_rules.series import SessionRv
from .history import SplicedRv, source_counts, splice
from .records import V5Record, v5_record

FORECASTERS = {  # v4's forecaster -> G14's
    V4_BASELINE_TRAILING: "v5c_trailing",
    V4_BASELINE_EWMA: "v5c_ewma_094",
    V4_BASELINE_HAR_DAILY: "v5c_har_daily",
    V4_BASELINE_HAR_INTRADAY: "v5c_har_intraday",
    V4_RULE_V1_CLOSE_BLEND: "v5c_close_blend",
}
CLOSES_ONLY = "closes"  # the input_sources of a forecaster that reads no intraday RV

Writer = Callable[[dict[str, V5Record]], int]  # one day's rows by forecaster, all or nothing


class V5Day:
    """v4's forecasters for one day `d`, their intraday input replaced by the splice for `d` and their method hash by
    G14's (`method.py`)."""

    def __init__(self, inputs: Inputs, candle: list[SessionRv], d: date, method_sha256: str):
        self.d = d
        self.spliced = splice(candle, inputs.intraday, d, cutoff(d))
        intraday = [s.rv for s in self.spliced]
        self.forecasts = DayForecasts(replace(inputs, intraday=intraday, method_sha256=method_sha256))

    def sources(self, v4_forecaster: str) -> str:
        """What each forecaster had to read: the trailing one the previous scored session's row only, HAR intraday
        the whole spliced series available at the cutoff (its fit window uses the latest of them), the rest closes."""
        if v4_forecaster == V4_BASELINE_HAR_INTRADAY:
            return source_counts(self.spliced)
        if v4_forecaster == V4_BASELINE_TRAILING:
            return source_counts(self._previous_session())
        return CLOSES_ONLY

    def _previous_session(self) -> list[SplicedRv]:
        sessions = self.forecasts.inputs.sessions
        earlier = before(sessions, self.d)
        return [s for s in self.spliced if earlier and s.rv.day == sessions[earlier - 1]]

    def v5_rows(self, g7_rows: dict[tuple[str, str], Record], made_on: str) -> dict[str, V5Record]:
        """G14's rows from v4's: V1's five, keyed by G14's forecaster."""
        return {
            FORECASTERS[f]: v5_record(row, self.sources(f), made_on)
            for (f, q), row in g7_rows.items()
            if q == V1_RV_1S and f in FORECASTERS
        }


def capture(day: V5Day, now: datetime, made_on: str, write: Writer) -> int:
    """Today's five rows through v4's own `capture_day` (its refusals unchanged); returns how many were added."""
    kept: dict[tuple[str, str], Record] = {}

    def keep(forecaster: str, question: str, rows: list[Record]) -> int:
        kept[(forecaster, question)] = rows[0]
        return 0

    capture_day(day.forecasts, day.d, now, keep)
    return write(day.v5_rows(kept, made_on))
