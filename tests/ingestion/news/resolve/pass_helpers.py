"""Builders of the NP2c tests: wrapper articles go into a local Record through the real gate; a pass reads them."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from fno.ingestion.news.article.keys import PUBLISHER, WRAPPER
from fno.ingestion.news.record.manifest import NewsManifest
from fno.ingestion.news.record.wrapper_index import WRAPPERS_FILE
from fno.ingestion.news.resolve.model import RESOLVED, LinkResolver, Resolved
from fno.ingestion.news.resolve.resolution_file import key_of_path
from fno.ingestion.news.resolve.run import ResolvePass
from fno.ingestion.news.write_once import WriteOnceWriter
from fno.ingestion.storage.data_store import DataStore
from fno.ingestion.storage.raw_store import AreaStore
from tests.ingestion.news.article.samples import rss, rss_item
from tests.ingestion.news.record.helpers import Setup

TODAY = date(2026, 10, 27)
WRAP_FEED, PUB_FEED = "feed-01", "feed-02"
PUBLISHER_URL = "https://outlet.example/story/{n}"


def wrapper_item(n: int, source_url: str = "https://outlet.example") -> str:
    return rss_item(
        title=f"Zzstory {n}", link=f"https://wrap.svc.example/rss/articles/CBMi{n:04d}?oc=5", guid=f"g-{n}",
        source="Outlet", source_url=source_url,
    )  # fmt: skip


def publisher_item(n: int) -> str:
    return rss_item(title=f"Zzpub {n}", link=f"https://pub.example/p/{n}", guid=f"p-{n}")


class FakeResolver(LinkResolver):
    """Answers from `answers` (link -> Resolved), else a fixed publisher URL; records every call."""

    def __init__(self, answers: dict | None = None):
        self.answers, self.calls, self.default = ({} if answers is None else answers), [], None

    def resolve(self, links):
        self.calls.append(list(links))
        ok = lambda link: self.default or Resolved(RESOLVED, PUBLISHER_URL.format(n=link[-8:-3]))  # noqa: E731
        return [self.answers.get(link) or ok(link) for link in links]


class World:
    def __init__(self, tmp_path, resolver: FakeResolver | None = None):
        self.record = Setup(tmp_path, kinds={WRAP_FEED: WRAPPER, PUB_FEED: PUBLISHER})
        self.drive, self.resolver = self.record.drive, resolver or FakeResolver()

    def add(self, *items: str, days_ago: int = 0, feed: str = WRAP_FEED) -> None:
        at = datetime(2026, 10, 27, 3, 0, tzinfo=UTC) - timedelta(days=days_ago)
        self.record.stage(rss(*items), feed=feed, at=at)
        self.record.promote(at.date())
        self.record.build()

    def pass_(self) -> ResolvePass:
        record = AreaStore(self.drive, "raw")
        store = DataStore(self.drive, "raw", self.record.receipts, "news-resolve", "run-1")
        manifest = NewsManifest(self.record.manifest_folder, "resolved.csv")
        writer = WriteOnceWriter(record, store, manifest, key_of_path)
        return ResolvePass(record, NewsManifest(self.record.manifest_folder, WRAPPERS_FILE), self.resolver, writer)

    def run(self, apply: bool = True, cap: int = 80):
        return self.pass_().run(TODAY, apply, cap)

    def resolution_files(self) -> list[str]:
        folder = self.drive.folder / "raw/news/resolved"
        return sorted(str(p.relative_to(self.drive.folder)) for p in folder.rglob("*.json")) if folder.exists() else []
