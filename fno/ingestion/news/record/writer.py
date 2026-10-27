"""The article writer (P2b2): the only code that puts a news article into the Record. One outcome per article, always:

- RECORDED: no file for this key yet; written (Drive, then receipt, then manifest row).
- NO_OP: the Record holds the key with the same fixed fields (first_seen_at is not compared). If the manifest row is
  missing (a stopped run) the SAME held bytes are saved again so the receipt and row exist.
- REVISION: the key is held with different fixed fields (a live blog, a correction, or two items that share a key):
  the first file stays the record; this version goes write-once to `news/revisions/<key[:2]>/<key>/<sha8>.json`, the
  sha8 being of the fixed fields so the same version seen in many polls is kept once. A key collision is therefore
  surfaced as a revision row, never hidden."""

from __future__ import annotations

import hashlib
from datetime import date

from fno.ingestion.news.article.article_file import Article
from fno.ingestion.news.record.manifest import RECORDED, NewsManifest
from fno.ingestion.news.record.planner import ArticlePlanner, Outcome
from fno.ingestion.news.record.wrapper_index import WrapperIndex
from fno.ingestion.storage.data_store import DataStore
from fno.ingestion.storage.raw_store import RawFileStore


class ArticleWriter:
    def __init__(
        self, reader: RawFileStore, store: DataStore, manifest: NewsManifest, wrappers: WrapperIndex | None = None
    ):
        """`reader`: the Record area, for reading only; `store`: the write path (Drive then receipt); `manifest`;
        `wrappers`: when given, the index that learns which recorded articles are Google News items (NP2d)."""
        self.planner, self.store, self.manifest, self.wrappers = ArticlePlanner(reader), store, manifest, wrappers

    def check_appendable(self) -> None:
        """TableFileBroken when a manifest this writer appends to ends in a torn line (before anything is written)."""
        self.manifest.check_appendable()
        if self.wrappers is not None:
            self.wrappers.check_appendable()

    def write(self, article: Article, day: date) -> Outcome:
        plan = self.planner.plan(article)
        if plan.outcome is Outcome.NO_OP:
            self._document(plan.path, plan.held, day, article.key, plan.status)
            self._mark(article, day, plan.status, plan.held)
            return Outcome.NO_OP
        data = article.to_bytes()
        self._save(plan.path, data, day, article.key, plan.status)
        self.planner.held[plan.path] = data
        self._mark(article, day, plan.status, data)
        return plan.outcome

    def _mark(self, article: Article, day: date, status: str, recorded: bytes) -> None:
        """Only the article file itself is indexed; a revision's first file was indexed when it was recorded."""
        if self.wrappers is not None and status == RECORDED:
            self.wrappers.mark(day, article, recorded)

    def _document(self, path: str, held: bytes, day: date, key: str, status: str) -> None:
        """Receipt and manifest row of a file already in Drive, when the row is missing (same bytes: no-op in Drive)."""
        if not self.manifest.has(key, status, hashlib.sha256(held).hexdigest()):
            self._save(path, held, day, key, status)

    def _save(self, path: str, data: bytes, day: date, key: str, status: str) -> None:
        self.store.put(path, data)
        self.manifest.add(day, key, status, hashlib.sha256(data).hexdigest(), len(data))
