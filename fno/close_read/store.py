"""Where A4h's files go: write-once into Drive's `data` area with a SHA-256 receipt (O9's `DataStore`), read back from
Drive by path; which files exist is read from the checkout's receipts, so no Drive listing is needed."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..storage.data_store import DataStore
from ..storage.raw_store import RawFileStore
from ..storage.receipts import ReceiptFolder
from .constants import DATA_AREA, ROOT


class ClosesStore(ABC):
    @abstractmethod
    def get(self, path: str) -> bytes | None: ...

    @abstractmethod
    def put(self, path: str, data: bytes) -> str:
        """Writes once and returns the bytes' SHA-256."""

    @abstractmethod
    def written(self) -> set[str]:
        """The paths (under `closes/`) already written."""


class DriveClosesStore(ClosesStore):
    def __init__(self, drive: RawFileStore, data: DataStore, receipts: ReceiptFolder):
        self.drive, self.data, self.receipts = drive, data, receipts

    def get(self, path: str) -> bytes | None:
        return self.drive.get(f"{DATA_AREA}/{path}")

    def put(self, path: str, data: bytes) -> str:
        return self.data.put(path, data).sha256

    def written(self) -> set[str]:
        prefix = f"{DATA_AREA}/"
        return {r.path.removeprefix(prefix) for r in self.receipts.under(f"{DATA_AREA}/{ROOT}")}
