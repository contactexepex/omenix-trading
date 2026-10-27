"""Builders of the NP4b tests: a Record with wrapper and publisher articles (through the real gate), the resolve
pass for the resolution files, a fake page fetcher (nothing is requested anywhere) and a fake clock."""

from __future__ import annotations

from fno.ingestion.news.pages import model
from fno.ingestion.news.pages.model import Page, PageFetcher
from fno.ingestion.news.reads.read_file import key_of_path
from fno.ingestion.news.reads.run import ReadPass
from fno.ingestion.news.record.manifest import NewsManifest
from fno.ingestion.news.record.wrapper_index import WRAPPERS_FILE
from fno.ingestion.news.sources.loader import build_source_rules
from fno.ingestion.news.write_once import WriteOnceWriter
from fno.ingestion.storage.data_store import DataStore
from fno.ingestion.storage.raw_store import AreaStore
from tests.ingestion.news.article.samples import rss, rss_item
from tests.ingestion.news.resolve.pass_helpers import TODAY, FakeResolver, wrapper_item
from tests.ingestion.news.resolve.pass_helpers import World as ResolveWorld

RULES = build_source_rules({"domains": {"outlet.example": {"tier": "tier1"}, "pub.example": {"tier": "tier1"}}})
HTML = b"""<html><head>
<script type="application/ld+json">{"@type":"NewsArticle","datePublished":"2026-10-27T08:00:00+05:30",
"author":{"@type":"Person","name":"Zz Writer"},"publisher":{"name":"Zz Outlet"},"articleBody":"%s"}</script>
</head><body>x</body></html>""" % (b"word " * 100)


class FakeFetcher(PageFetcher):
    def __init__(self, answers=None, on_fetch=None):
        self.answers, self.asked, self.seconds, self.on_fetch = answers or {}, [], [], on_fetch

    def fetch(self, url, seconds=None):
        self.asked.append(url)
        self.seconds.append(seconds)
        if self.on_fetch:
            self.on_fetch()
        return self.answers.get(url) or Page(model.OK, url, "text/html", body=HTML)


class Clock:
    def __init__(self):
        self.now = 0.0

    def time(self):
        return self.now


def publisher_page_item(n: int) -> str:
    return rss_item(title=f"Zzpub {n}", link=f"https://pub.example/p/{n}", guid=f"p-{n}")


class World(ResolveWorld):
    """The resolve World, plus publisher articles and a read pass over what it recorded."""

    def __init__(self, tmp_path):
        super().__init__(tmp_path, FakeResolver())
        self.fetcher, self.clock = FakeFetcher(), Clock()

    def add_publisher(self, *numbers: int, days_ago: int = 0) -> None:
        self.add(*[publisher_page_item(n) for n in numbers], days_ago=days_ago, feed="feed-02")

    def resolve_all(self) -> None:
        self.run()  # the resolve pass writes the resolution files and resolved.csv

    def read_pass(self, reads_file: str = "reads.csv") -> ReadPass:
        record = AreaStore(self.drive, "raw")
        store = DataStore(self.drive, "raw", self.record.receipts, "news-read", "run-1")
        folder = self.record.manifest_folder
        writer = WriteOnceWriter(record, store, NewsManifest(folder, reads_file), key_of_path)
        return ReadPass(record, NewsManifest(folder), NewsManifest(folder, WRAPPERS_FILE),
                        NewsManifest(folder, "resolved.csv"), self.fetcher, RULES, writer, self.clock.time)  # fmt: skip

    def read(self, apply: bool = True, pages: int = 80, budget: float = 900.0):
        return self.read_pass().run(TODAY, apply, pages, budget)

    def read_files(self) -> list[str]:
        folder = self.drive.folder / "raw/news/reads"
        return sorted(str(p.relative_to(self.drive.folder)) for p in folder.rglob("*.json")) if folder.exists() else []


__all__ = ["World", "wrapper_item", "rss", "TODAY", "FakeFetcher", "Page", "RULES", "HTML"]
