"""Where G13's files go (section 5): write-once into Drive's `data` area with a SHA-256 receipt (O9's `DataStore`),
read back from Drive by path. Behind an interface so a test or another store swaps in one class."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..storage.data_store import DataStore
from ..storage.raw_store import RawFileStore
from .folders import DATA_AREA


class DistributionStore(ABC):
    @abstractmethod
    def get(self, path: str) -> bytes | None:
        """A file already written, or None."""

    @abstractmethod
    def put(self, path: str, data: bytes) -> None:
        """Writes once and records its receipt; the same bytes again only restore the receipt."""


class DriveDistributionStore(DistributionStore):
    def __init__(self, drive: RawFileStore, data: DataStore):
        self.drive, self.data = drive, data

    def get(self, path: str) -> bytes | None:
        return self.drive.get(f"{DATA_AREA}/{path}")

    def put(self, path: str, data: bytes) -> None:
        self.data.put(path, data)
