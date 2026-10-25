"""Where versions come from (story DR1). `StagingArea` saves every fetch under a writer-unique name
(`data/staging/<dataset>/<session>/<fetched_at>_<run_id><suffix>`), so two writers can never meet on one name (audit
items 2, 3 and 5), and lists a session's versions from their receipts. `ReceiptedFiles` names files a dataset already
writes (the shadow phase: the existing writer is unchanged)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable
from datetime import UTC, datetime

from ..storage.data_store import DataStore
from ..storage.receipts import Receipt, ReceiptFolder
from .constants import DATA_AREA, STAGED_NAME, STAGING_ROOT
from .models import StagedVersion


class VersionSource(ABC):
    @abstractmethod
    def versions(self, session: str) -> list[StagedVersion]:
        """Every saved version of the session, in a stable order."""


def staged_version(receipt: Receipt) -> StagedVersion:
    return StagedVersion(receipt.path, receipt.sha256, receipt.size, receipt.written_at)


class StagingArea(VersionSource):
    def __init__(self, dataset: str, store: DataStore, receipts: ReceiptFolder, clock: Callable[[], datetime]):
        """`store`: O9's data store (area `data`), whose run id makes each name unique to its writer."""
        self.dataset, self.store, self.receipts, self.clock = dataset, store, receipts, clock

    def stage(self, session: str, data: bytes, suffix: str) -> StagedVersion:
        fetched_at = self.clock().astimezone(UTC)
        name = STAGED_NAME.format(fetched_at=fetched_at, run_id=self.store.run_id, suffix=suffix)
        return staged_version(self.store.put(f"{STAGING_ROOT}/{self.dataset}/{session}/{name}", data))

    def versions(self, session: str) -> list[StagedVersion]:
        folder = f"{DATA_AREA}/{STAGING_ROOT}/{self.dataset}/{session}"
        return [staged_version(receipt) for receipt in self.receipts.under(folder)]


class ReceiptedFiles(VersionSource):
    def __init__(self, receipts: ReceiptFolder, paths: Callable[[str], Iterable[str]]):
        """`paths`: the Drive paths (area included) a session's versions are saved at."""
        self.receipts, self.paths = receipts, paths

    def versions(self, session: str) -> list[StagedVersion]:
        found = (self.receipts.read(path) for path in self.paths(session))
        return [staged_version(receipt) for receipt in found if receipt is not None]
