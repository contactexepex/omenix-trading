"""One candle-close realised-variance record per session (story A16b), one file each, beside A16's `rv/` and never in
it: `rv-candle/<YYYY>/nifty_rv_candle_<YYYYMMDD>.csv`. A16's table rules (written once; the same inputs again change
nothing; other inputs are refused) with A16's columns plus provenance, the NSE check and the copies used."""

from __future__ import annotations

from .rv_table import FIELDS as A16_FIELDS
from .rv_table import RvTable

FIELDS = (
    *A16_FIELDS, "provenance", "nse_check", "nse_open_gap", "nse_high_gap", "nse_low_gap", "outside_candles",
    "copy_15m", "copy_1m",
)  # fmt: skip


class CandleRvTable(RvTable):
    fields = FIELDS
    file_name = "rv-candle/{day:%Y}/nifty_rv_candle_{day:%Y%m%d}.csv"
    pattern = "rv-candle/*/nifty_rv_candle_*.csv"
