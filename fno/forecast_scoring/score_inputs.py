"""The forecasts story G4 scores, in one shape whatever their record version.

- **History back-fill** (protocol v1, `close_proxy`): the frozen v1 record carries the day's IV30 state inside
  `method_or_version` (`.../iv30:flagged`, story G2's back-fill).
- **Live** (protocol v2, `live_1500_proxy`): the v2 record's `iv30_status` column; a record generated after 15:15 IST on
  its day is not scored (protocol v2 section 5) and is counted as late.
History and live forecasts are scored and reported apart (protocol v2 section 7), never mixed.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from ..forecast.schema import ForecastRecord
from ..forecast.schema_v2 import INPUT_MODES, ForecastRecordV2

CLOSE_PROXY, LIVE = INPUT_MODES
IV30_STATE_PREFIX = "iv30:"


@dataclass(frozen=True)
class ScoredForecast:
    mode: str  # close_proxy or live_1500_proxy
    book: str  # a book or a baseline
    day: date
    question: str
    probability: float | None  # None: "no forecast" recorded
    iv30_status: str  # interpolated, flagged or none: the forecast's input quality


def from_backfill(record: ForecastRecord) -> ScoredForecast:
    states = [part for part in record.method_or_version.split("/") if part.startswith(IV30_STATE_PREFIX)]
    if len(states) != 1:
        raise ValueError(f"back-fill record without one IV30 state: {record.method_or_version!r}")
    status = states[0].removeprefix(IV30_STATE_PREFIX)
    return ScoredForecast(CLOSE_PROXY, record.book, record.date, record.question, record.probability, status)


def from_live(record: ForecastRecordV2) -> ScoredForecast | None:
    """None when the record was generated after its deadline (not scored)."""
    if not record.on_time:
        return None
    r = record.record
    return ScoredForecast(record.input_mode, r.book, r.date, r.question, r.probability, record.iv30_status)
