"""Where the weekly audit draw's close comes from (judge 62 addendum 2): NSE's index-close file as first archived in the
owner's Drive, which the AI books' routines cannot reach (they have no Drive access), never the repository's closes
file, which any routine with push access could edit before the draw. `CloseArchive` is the interface;
`DriveIndexCloseArchive` reads the raw area (the first archived version; NSE's later versions live in revisions)."""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from datetime import date

from ..constants import INDEX_NIFTY_50
from ..fo_bhavcopy import BadFile, read_index_closes
from ..storage.raw_source import NseIndexCloseSource
from ..storage.raw_store import RawFileStore


class SeedRefused(RuntimeError):
    """The archive cannot confirm the close: the week is not drawn (fails closed) and #fno-desk is told."""


class CloseArchive(ABC):
    @abstractmethod
    def nifty_close(self, day: date, sha256: str) -> float:
        """NIFTY 50's close of `day` from the archived file whose SHA-256 is `sha256`, or SeedRefused."""

    @abstractmethod
    def has_file(self, day: date) -> bool:
        """Whether an index-close file for `day` is archived (a session took place that day)."""


class DriveIndexCloseArchive(CloseArchive):
    def __init__(self, raw: RawFileStore):
        self.raw = raw

    def nifty_close(self, day: date, sha256: str) -> float:
        path = NseIndexCloseSource.path_for(day)
        data = self.raw.get(path)
        if data is None:
            raise SeedRefused(f"{day}: no index-close file archived at raw/{path}")
        if hashlib.sha256(data).hexdigest() != sha256:
            raise SeedRefused(f"{day}: the archived index-close file is not the one the closes file names")
        try:
            closes = read_index_closes(data, NseIndexCloseSource.filename_for(day))
        except BadFile as error:
            raise SeedRefused(f"{day}: {error}") from None
        if INDEX_NIFTY_50 not in closes:
            raise SeedRefused(f"{day}: the archived file has no {INDEX_NIFTY_50} close")
        return closes[INDEX_NIFTY_50]

    def has_file(self, day: date) -> bool:
        return self.raw.get(NseIndexCloseSource.path_for(day)) is not None


class NoCloseArchive(CloseArchive):
    """No Drive settings: no week can be confirmed, so none is drawn (its sessions stay pending)."""

    def nifty_close(self, day: date, sha256: str) -> float:
        raise SeedRefused(f"{day}: Drive is not configured, so the close cannot be confirmed")

    def has_file(self, day: date) -> bool:
        raise SeedRefused(f"{day}: Drive is not configured, so the week's sessions cannot be confirmed")
