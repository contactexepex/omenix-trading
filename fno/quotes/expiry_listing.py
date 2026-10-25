"""Where the quote recorder learns which expiries are listed when the broker's own list falls short (story A4).

Groww's expiry list refuses future years, so in late December it cannot list January. NSE's daily F&O file lists every
expiry of every contract (on 9 Oct 2026: NIFTY out to June 2031). The latest file of the last few days is read, its
name and SHA-256 kept as provenance; if none is recent enough the caller fails closed.
"""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from datetime import date, timedelta

from ..fo_bhavcopy import read_fo_file
from ..storage.raw_library import RawFileLibrary
from ..storage.raw_source import NseDailyFoSource

LOOKBACK_DAYS = 7  # a listing older than a week is too stale to trust
INDEX_OPTION = "IDO"


class ExpiryListUnavailable(RuntimeError):
    """No recent listing could be read."""


class ListedExpiries(ABC):
    @abstractmethod
    def listed(self, underlying: str, today: date) -> tuple[list[date], dict]:
        """Every listed option expiry of the underlying, and where the list came from (file, date, SHA-256)."""


class ExpiryHistory(ABC):
    @abstractmethod
    def listed_on(self, underlying: str, day: date) -> tuple[date, list[date], dict]:
        """What NSE had listed by `day`: the date of its latest file on or before `day`, every option expiry of the
        underlying in it, and where it came from."""


class NseDailyFileExpiries(ListedExpiries, ExpiryHistory):
    def __init__(self, library: RawFileLibrary):
        self.library = library
        self._files: dict[date, tuple[list[dict], dict] | None] = {}  # a day's file, read and parsed once a run (A4c)

    def listed(self, underlying: str, today: date) -> tuple[list[date], dict]:
        return self._latest(underlying, today - timedelta(days=1))[1:]

    def listed_on(self, underlying: str, day: date) -> tuple[date, list[date], dict]:
        return self._latest(underlying, day)

    def _latest(self, underlying: str, last_day: date) -> tuple[date, list[date], dict]:
        """The newest file from `last_day` back over LOOKBACK_DAYS days."""
        for back in range(LOOKBACK_DAYS):
            day = last_day - timedelta(days=back)
            file = self._file(day)
            if file is None:
                continue
            rows, provenance = file
            expiries = sorted(
                {
                    date.fromisoformat(r["XpryDt"])
                    for r in rows
                    if r["FinInstrmTp"] == INDEX_OPTION and r["TckrSymb"] == underlying
                }
            )
            return day, expiries, provenance
        raise ExpiryListUnavailable(f"no NSE F&O file in the {LOOKBACK_DAYS} days up to {last_day}")

    def _file(self, day: date) -> tuple[list[dict], dict] | None:
        """The day's parsed rows and provenance, or None when the day has no file (about 0.8 s a parse)."""
        if day not in self._files:
            path = NseDailyFoSource.path_for(day)
            found = self.library.get(path)
            self._files[day] = None if found.data is None else (
                read_fo_file(NseDailyFoSource.filename_for(day), found.data),
                {"source": found.origin, "file": path, "file_date": day.isoformat(),
                 "sha256": hashlib.sha256(found.data).hexdigest()},
            )  # fmt: skip
        return self._files[day]
