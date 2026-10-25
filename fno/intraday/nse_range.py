"""NSE's official NIFTY 50 open, high and low for a session (A1/A10's index-close file), and the check of the candle
levels against them (story A16b). A level, or a used candle's high or low, outside NSE's official range means the feed
was wrong that session (23 Mar 2020: one high 196.30 points above NSE's), so the session is void. Gaps are kept as
differences of NSE's figures, never as a level."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass

from .candle_levels import Candle
from .minute_check import beyond

NIFTY_ROW, OPEN, HIGH, LOW = "NIFTY 50", "Open Index Value", "High Index Value", "Low Index Value"


@dataclass(frozen=True)
class NseDay:
    open: float
    high: float
    low: float


@dataclass(frozen=True)
class RangeCheck:
    outside: bool
    high_gap: float | None  # NSE's high minus the highest used candle high
    low_gap: float | None  # the lowest used candle low minus NSE's low
    open_gap: float | None  # the last pre-open 1-minute close minus NSE's open (None without a 1-minute answer)


def read_nse_day(data: bytes, index_row: str = NIFTY_ROW) -> NseDay:
    """An index's row of an index-close file (NIFTY 50's by default; A22d also reads NIFTY BANK's); ValueError when the
    file does not have it."""
    for row in csv.DictReader(io.StringIO(data.decode("utf-8", errors="replace"))):
        if (row.get("Index Name") or "").strip().upper() == index_row:
            try:
                return NseDay(float(row[OPEN]), float(row[HIGH]), float(row[LOW]))
            except (KeyError, TypeError) as exc:  # a column missing or a short row: unreadable, as a bad number is
                raise ValueError(f"the {index_row} row lacks a value: {type(exc).__name__}") from None
    raise ValueError(f"no {index_row} row in the index-close file")


def check_range(
    levels: tuple[float | None, ...], used: tuple[Candle, ...], nse: NseDay, pre_open_close: float | None
) -> RangeCheck:
    values = [v for v in levels if v is not None] + [c.high for c in used] + [c.low for c in used]
    outside = any((v > nse.high and beyond(v - nse.high)) or (v < nse.low and beyond(nse.low - v)) for v in values)
    high_gap = round(nse.high - max(c.high for c in used), 2) if used else None
    low_gap = round(min(c.low for c in used) - nse.low, 2) if used else None
    open_gap = None if pre_open_close is None else round(pre_open_close - nse.open, 2)
    return RangeCheck(outside, high_gap, low_gap, open_gap)
