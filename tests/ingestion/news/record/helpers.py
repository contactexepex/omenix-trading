"""Shared builders of the P2b2 tests: a local Drive, a local checkout, and staged synthetic polls (no network)."""

from __future__ import annotations

from datetime import UTC, datetime

from fno.ingestion.news.article.keys import PUBLISHER
from fno.ingestion.news.fetcher import SOURCE
from fno.ingestion.news.record.gate import NewsGate
from fno.ingestion.news.record.manifest import NewsManifest
from fno.ingestion.news.record.wrapper_index import WrapperIndex
from fno.ingestion.news.record.writer import ArticleWriter
from fno.ingestion.promotion.staging import StagingArea
from fno.ingestion.storage.data_store import DataStore
from fno.ingestion.storage.raw_store import AreaStore, LocalFolderStore
from fno.ingestion.storage.receipts import ReceiptFolder

POLL_AT = datetime(2026, 10, 27, 3, 0, 0, tzinfo=UTC)
FEED = "feed-01"


class Setup:
    def __init__(self, tmp_path, kinds=None):
        self.drive = LocalFolderStore(tmp_path / "drive")
        self.receipts = ReceiptFolder(tmp_path / "repo" / "receipts")
        self.manifest_folder = tmp_path / "repo" / "manifests"
        self.staging = StagingArea(AreaStore(self.drive, "staging"))
        self.kinds = kinds if kinds is not None else {FEED: PUBLISHER}
        self.build()

    def build(self) -> None:
        """A fresh run: new writer, new manifest read from disk, new per-run cache (as the next process would have)."""
        store = DataStore(self.drive, "raw", self.receipts, "news-promote", "run-1")
        self.manifest = NewsManifest(self.manifest_folder)
        self.wrappers = WrapperIndex(self.manifest_folder)
        self.writer = ArticleWriter(AreaStore(self.drive, "raw"), store, self.manifest, self.wrappers)
        self.gate = NewsGate(self.staging, self.writer, self.kinds)

    def stage(self, data: bytes, feed: str = FEED, at: datetime = POLL_AT) -> None:
        self.staging.stage(SOURCE, f"{feed}/{at:%Y/%m/%d}/poll", data, at)

    def promote(self, day=None):
        day = day or POLL_AT.date()
        return self.gate.promote(day, day)

    def record_files(self) -> list[str]:
        return sorted(str(p.relative_to(self.drive.folder)) for p in (self.drive.folder / "raw").rglob("*.json"))

    def manifest_text(self) -> str:
        return (
            (self.manifest_folder / "articles.csv").read_text()
            if (self.manifest_folder / "articles.csv").exists()
            else ""
        )
