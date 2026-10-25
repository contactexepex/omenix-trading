"""An index's close on a session from NSE's archived index-close file (story MS-SIM-d1, criterion 10).

Legacy-format F&O files carry no underlying price, so `BhavcopyChain` asks this for the close. The file comes through
the stores-only library, so a day whose file is not archived has no close (None) and its road closes
(`capture_missing`)."""

from datetime import date
from functools import lru_cache

from ....fo_bhavcopy import INDEX_NAMES, BadFile, read_index_closes
from ....research_data.nifty_panel import DailyFiles

CACHED_DAYS = 64  # the drivers' history window slides one session at a time


class ArchivedIndexCloses:
    def __init__(self, files: DailyFiles):
        self.files = files
        self._closes = lru_cache(maxsize=CACHED_DAYS)(self._read)

    def __call__(self, underlying: str, session: date) -> float | None:
        name = INDEX_NAMES.get(underlying)
        return self._closes(session).get(name) if name else None

    def _read(self, session: date) -> dict[str, float]:
        if not self.files.covers(session):
            return {}
        name, data = self.files.get(session)
        if data is None:
            return {}
        try:
            return read_index_closes(data, name)
        except BadFile:
            return {}
