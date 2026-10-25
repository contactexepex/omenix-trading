"""Archives today's copy of an NSE reference list (story P6): fetched, checked, saved under the day's folder with its
manifest row (through the archive store). A copy already archived for the day is kept; a different one is refused."""

from __future__ import annotations

from datetime import date

from .coverage import Validator
from .raw_source import NseArchiveSource
from .raw_store import RawFileStore

TAKEN = "{path}: archived ({size} bytes)"
ALREADY = "{path}: already archived for this day"
NOT_SERVED = "{path}: NSE does not serve it now"


class SnapshotTaker:
    def __init__(self, store: RawFileStore, source: NseArchiveSource, validate: Validator):
        self.store, self.source, self.validate = store, source, validate

    def take(self, day: date) -> str:
        """One line saying what happened; ValueError when NSE's copy fails its check (nothing is saved)."""
        return self.take_path(self.source.path_for(day))

    def take_path(self, path: str) -> str:
        """The same for an explicit archive path of the source (a symbol's own list)."""
        existing = self.store.get(path)
        if existing is not None:
            self.store.put(path, existing)  # the same bytes: the store keeps them; the archive's manifest gets its row
            return ALREADY.format(path=path)
        data = self.source.fetch(path)
        if data is None:
            return NOT_SERVED.format(path=path)
        self.validate(path.rsplit("/", 1)[-1], data)
        self.store.put(path, data)
        return TAKEN.format(path=path, size=len(data))
