"""Which batches a download job has (story O6). `BatchFinder` is the interface; `ManifestBatches` reads what the
download already committed: one dated dataset's manifest rows (A10, one file per day) and its revision rows (A11, a
later version NSE published). Each becomes a pointer whose version is the SHA-256 of those bytes, so a republished
file is a new pointer while the original stays as it was."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from ..storage.manifest_folder import ManifestFolder
from ..storage.raw_source import NseArchiveSource
from ..storage.revisions import RevisionIndex
from .pointer import BatchPointer


class BatchFinder(ABC):
    @abstractmethod
    def batches(self) -> list[BatchPointer]:
        """Every batch and version the job holds in its window, oldest first."""


class ManifestBatches(BatchFinder):
    def __init__(
        self,
        source: type[NseArchiveSource],
        manifests: ManifestFolder,
        revisions: RevisionIndex,
        since: date,
        areas: tuple[str, str],
    ):
        self.source, self.manifests, self.revisions, self.since = source, manifests, revisions, since
        self.raw_area, self.revisions_area = areas

    def batches(self) -> list[BatchPointer]:
        dataset = self.source.dataset
        originals = [
            BatchPointer(dataset, f.day.isoformat(), f.sha256, f"{self.raw_area}/{self.source.path_for(f.day)}")
            for f in self.manifests.read(self.source)
            if f.day >= self.since
        ]
        later = [
            BatchPointer(dataset, r.day.isoformat(), r.sha256, f"{self.revisions_area}/{r.revision_path}")
            for r in self.revisions.read(self.source)
            if r.found_at.date() >= self.since
        ]
        return sorted(originals + later)
