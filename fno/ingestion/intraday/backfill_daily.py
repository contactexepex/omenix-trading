"""The candle back-fill's repository files in the daily run (story A16b-d): the files it writes, which O1 commits and
nothing else. Kept apart from `backfill_wiring.py`, which builds Groww's client, so the daily run names these without
importing any Groww code."""

from __future__ import annotations

from pathlib import Path

from fno.ingestion.storage.wiring import REPOSITORY

CANDLE_FOLDER = REPOSITORY / "research" / "data" / "intraday"  # the rows go under rv-candle/ (A16's rv/ is apart)
TABLE_FOLDER = Path("rv-candle")
DEFERRALS = TABLE_FOLDER / "deferred.csv"
MANIFESTS = Path("groww-candles")
