"""NSE's index-close file for a session, read through A1's library (Drive first, then NSE), with the one distinction
the back-fill needs (story A16b, judge 122 addendum 2): **absent** only when Drive has no copy and NSE answers 404
(the library's `RawFile(None)`); any failed read (a Drive error, NSE unavailable after A9b's retries or refusing, an
unreadable file) is **transient**: the session waits for the next run, never a void row."""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date

import requests

from ..storage.raw_library import RawFileLibrary
from ..storage.raw_source import NseIndexCloseSource, RawSourceUnavailable
from .nse_range import NseDay, read_nse_day

READ_FAILURES = (RawSourceUnavailable, requests.RequestException, OSError, RuntimeError, ValueError)


class NseReadFailed(RuntimeError):
    """The file could not be read now: transient."""


@dataclass(frozen=True)
class NseReading:
    day: NseDay | None  # None: definitively absent
    sha256: str  # of the file's bytes ("" when absent)


class NseDays(ABC):
    @abstractmethod
    def read(self, day: date) -> NseReading:
        """NSE's official open, high and low for `day`; NseReading(None, "") when definitively absent; NseReadFailed
        when the read failed (transient)."""


class NseIndexDays(NseDays):
    """NSE's index-close files through A1's library."""

    def __init__(self, library: RawFileLibrary):
        self.library = library

    def read(self, day: date) -> NseReading:
        try:
            found = self.library.get(NseIndexCloseSource.path_for(day))
            if found.data is None:
                return NseReading(None, "")
            return NseReading(read_nse_day(found.data), hashlib.sha256(found.data).hexdigest())
        except READ_FAILURES as exc:
            raise NseReadFailed(f"NSE index-close {day}: {type(exc).__name__}") from None
