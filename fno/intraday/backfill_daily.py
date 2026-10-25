"""The candle back-fill's place in the daily run (story A16b-d): its command, the time it may start and the repository
files it writes, which O1 commits and nothing else. Kept apart from `backfill_wiring.py`, which builds Groww's client,
so the daily run names these without importing any Groww code."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

from ..storage.manifest_folder import ManifestFolder
from ..storage.raw_source import NseIndexCloseSource
from ..storage.wiring import MANIFEST_FOLDER, REPOSITORY
from .backfill_cli import BACKFILL
from .slots import FIRST_MARK, MARK_STEP, MARKS_PER_SESSION

CATCH_UP_COMMAND = ("intraday", BACKFILL)  # no dates: up to the latest finished session, held windows not fetched
CANDLE_FOLDER = REPOSITORY / "research" / "data" / "intraday"  # the rows go under rv-candle/ (A16's rv/ is apart)
TABLE_FOLDER = Path("rv-candle")
DEFERRALS = TABLE_FOLDER / "deferred.csv"
MANIFESTS = Path("groww-candles")
# Two runs on one Groww key lose quotes to its rate limit (A16, `claims.py`): start after A16's last mark has ended
AFTER_LAST_MARK = timedelta(minutes=3)
CATCH_UP_FROM = (
    datetime.combine(date.min, FIRST_MARK) + (MARKS_PER_SESSION - 1) * MARK_STEP + AFTER_LAST_MARK
).time()  # 15:33 IST


def candle_folders() -> tuple[str, ...]:
    """Repository-relative: the rows and deferrals, the candle manifests, and the A9 manifest of NSE's index-close
    files (a row only when the back-fill had to fetch a file not yet in Drive)."""
    index_close = ManifestFolder(MANIFEST_FOLDER).path_for(NseIndexCloseSource)
    folders = (CANDLE_FOLDER / TABLE_FOLDER, MANIFEST_FOLDER / MANIFESTS)
    return (
        *(f"{p.relative_to(REPOSITORY).as_posix()}/" for p in folders),
        index_close.relative_to(REPOSITORY).as_posix(),
    )
