"""The open check's view of A22's own Drive files (story A22d): whether a file has a receipt (the checkout's
`receipts/` tree, no Drive call) and its bytes, read through O9's verified Drive cache, never trusted unverified."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..storage.drive_cache import DriveCache
from ..storage.receipts import ReceiptFolder


class UnreadableFile(RuntimeError):
    """A receipted file missing from Drive or different from its receipt."""


class PreopenFiles(ABC):
    @abstractmethod
    def has(self, path: str) -> bool:
        """True when the file (a path under A22's Drive area) has a receipt."""

    @abstractmethod
    def read(self, path: str) -> bytes:
        """The file's verified bytes; UnreadableFile when Drive cannot give them."""


class DriveCacheFiles(PreopenFiles):
    def __init__(self, cache: DriveCache, receipts: ReceiptFolder, area: str):
        self.cache, self.receipts, self.area = cache, receipts, area

    def has(self, path: str) -> bool:
        return self.receipts.read(f"{self.area}/{path}") is not None

    def read(self, path: str) -> bytes:
        drive_path = f"{self.area}/{path}"
        report = self.cache.sync(drive_path)
        if report.problems:
            raise UnreadableFile(report.problems[0])
        return self.cache.local(drive_path).read_bytes()
