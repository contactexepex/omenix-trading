"""Where a clustering run gets its articles (P2d): the Record, READ ONLY. Which articles to read comes from the news
manifest in the checkout (ids recorded on or after a day), so a run does not list or read every article ever recorded.
The net is wider than the window by a margin; the exact window rule is P2c's. A recorded article whose file is missing
or damaged is counted, never skipped silently (the run then writes nothing).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from fno.ingestion.news.article.article_file import Article, article_from_bytes
from fno.ingestion.news.cluster.window import WINDOW
from fno.ingestion.news.record.manifest import NewsManifest
from fno.ingestion.news.record.planner import article_path
from fno.ingestion.storage.raw_store import RawFileStore

MARGIN = timedelta(days=2)  # a poll's day is recorded in UTC, a window edge can fall mid-day, a promote can run late


@dataclass(frozen=True)
class Candidates:
    articles: tuple[Article, ...]
    unreadable: int


class ArticleSource:
    def __init__(self, record: RawFileStore, manifest: NewsManifest):
        """`record`: the Record area, read only (this class has no way to write); `manifest`: the articles manifest."""
        self.record, self.manifest = record, manifest

    @property
    def skipped_rows(self) -> int:
        """Rows of the articles manifest that are not whole: each may hide an article, so a run reports them."""
        return self.manifest.skipped

    def candidates(self, as_of: datetime) -> Candidates:
        net = (as_of - WINDOW - MARGIN).date()
        found, unreadable = [], 0
        for key in self.manifest.recorded_since(net):
            try:
                data = self.record.get(article_path(key))
                found.append(article_from_bytes(data))
            except Exception:  # noqa: BLE001 - a missing file (None) or a damaged one: both counted, nothing is named
                unreadable += 1
        return Candidates(tuple(found), unreadable)
