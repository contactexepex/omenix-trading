"""Builders of the P2d tests: articles go into a local Record through the real P2b2 gate; a cluster run reads them."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fno.ingestion.news.cluster import cluster as clustering_module
from fno.ingestion.news.cluster_record.article_source import ArticleSource
from fno.ingestion.news.cluster_record.run import ClusterRun
from fno.ingestion.news.cluster_record.writer import ClusterWriter
from fno.ingestion.news.record.manifest import NewsManifest
from fno.ingestion.storage.data_store import DataStore
from fno.ingestion.storage.raw_store import AreaStore
from tests.ingestion.news.article.samples import rss, rss_item
from tests.ingestion.news.record.helpers import POLL_AT, Setup

AS_OF = datetime(2026, 10, 27, 12, 0, 0, tzinfo=UTC)
HEADLINE = "Nifty ends higher as IT stocks rally"
OTHER = "RBI keeps repo rate unchanged at 6.5 per cent"


def item(title: str, link: str, hour: int = 8) -> str:
    return rss_item(title=title, link=link, pub=f"Tue, 27 Oct 2026 {hour:02d}:00:00 +0000")


class World:
    """A Record with articles in it (made by the real gate) and a cluster run over it."""

    def __init__(self, tmp_path):
        self.record = Setup(tmp_path)
        self.drive = self.record.drive
        self.build()

    def build(self) -> None:
        """A fresh run: manifests are read again from disk, as the next process would."""
        record = AreaStore(self.drive, "raw")
        store = DataStore(self.drive, "raw", self.record.receipts, "news-cluster", "run-1")
        self.clusters = NewsManifest(self.record.manifest_folder, "clusters.csv")
        writer = ClusterWriter(record, store, self.clusters)
        self.run_object = ClusterRun(ArticleSource(record, NewsManifest(self.record.manifest_folder)), writer, record)

    def add(self, *items: str, hours_after: int = 0) -> None:
        self.record.stage(rss(*items), at=POLL_AT + timedelta(hours=hours_after))
        self.record.promote()
        self.build()

    def cluster(self, as_of: datetime = AS_OF):
        return self.run_object.run(as_of)

    def cluster_files(self) -> list[str]:
        return sorted(
            str(p.relative_to(self.drive.folder)) for p in (self.drive.folder / "raw/news/clusters").rglob("*.json")
        )

    def version(self) -> str:
        return clustering_module.ALGORITHM_VERSION
