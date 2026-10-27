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
from fno.ingestion.news.record.manifest import NewsManifest
from fno.ingestion.news.record.planner import ArticlePlanner, Outcome
from fno.ingestion.storage.data_store import DataStore
from fno.ingestion.storage.raw_store import RawFileStore


class ArticleWriter:
    def __init__(self, reader: RawFileStore, store: DataStore, manifest: NewsManifest):
        """`reader`: the Record area, for reading only; `store`: the write path (Drive then receipt); `manifest`."""
        self.planner, self.store, self.manifest = ArticlePlanner(reader), store, manifest

    def write(self, article: Article, day: date) -> Outcome:
        plan = self.planner.plan(article)
        if plan.outcome is Outcome.NO_OP:
            self._document(plan.path, plan.held, day, article.key, plan.status)
            return Outcome.NO_OP
        data = article.to_bytes()
        self._save(plan.path, data, day, article.key, plan.status)
        self.planner.held[plan.path] = data
        return plan.outcome

    def _document(self, path: str, held: bytes, day: date, key: str, status: str) -> None:
        """Receipt and manifest row of a file already in Drive, when the row is missing (same bytes: no-op in Drive)."""
        if not self.manifest.has(key, status, hashlib.sha256(held).hexdigest()):
            self._save(path, held, day, key, status)

    def _save(self, path: str, data: bytes, day: date, key: str, status: str) -> None:
        self.store.put(path, data)
        self.manifest.add(day, key, status, hashlib.sha256(data).hexdigest(), len(data))
