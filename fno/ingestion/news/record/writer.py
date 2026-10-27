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
import json
from datetime import date
from enum import Enum

from fno.ingestion.news.article.article_file import Article
from fno.ingestion.news.record.manifest import RECORDED, REVISION, NewsManifest
from fno.ingestion.storage.data_store import DataStore
from fno.ingestion.storage.raw_store import RawFileConflict, RawFileStore

ARTICLES, REVISIONS = "news/articles", "news/revisions"
UNCOMPARED = ("first_seen_at", "format")


class Outcome(Enum):
    RECORDED = "recorded"
    REVISION = "revision"
    NO_OP = "no_op"


def article_path(key: str) -> str:
    return f"{ARTICLES}/{key[:2]}/{key}.json"


def _fixed(data: bytes) -> bytes | None:
    try:
        document = json.loads(data)
        return json.dumps({k: v for k, v in document.items() if k not in UNCOMPARED}, sort_keys=True).encode()
    except (ValueError, AttributeError):
        return None  # a damaged held file differs from every article


class ArticleWriter:
    def __init__(self, reader: RawFileStore, store: DataStore, manifest: NewsManifest):
        """`reader`: the Record area, for reading only; `store`: the write path (Drive then receipt); `manifest`."""
        self.reader, self.store, self.manifest = reader, store, manifest
        self.held: dict[str, bytes | None] = {}  # one Drive read per key per run, however many polls repeat it

    def write(self, article: Article, day: date) -> Outcome:
        path, data = article_path(article.key), article.to_bytes()
        held = self._held(path)
        if held is None:
            self._save(path, data, day, article.key, RECORDED)
            self.held[path] = data
            return Outcome.RECORDED
        if _fixed(held) is not None and _fixed(held) == _fixed(data):
            self._document(path, held, day, article.key, RECORDED)
            return Outcome.NO_OP
        return self._revision(article, data, day)

    def _revision(self, article: Article, data: bytes, day: date) -> Outcome:
        sha8 = hashlib.sha256(_fixed(data) or b"").hexdigest()[:8]
        path = f"{REVISIONS}/{article.key[:2]}/{article.key}/{sha8}.json"
        held = self._held(path)
        if held is not None:
            if _fixed(held) != _fixed(data):  # the same 8 hex characters for two versions: never called a no-op
                raise RawFileConflict(f"{path}: revision name collision")
            self._document(path, held, day, article.key, REVISION)
            return Outcome.NO_OP
        self._save(path, data, day, article.key, REVISION)
        self.held[path] = data
        return Outcome.REVISION

    def _held(self, path: str) -> bytes | None:
        if path not in self.held:
            self.held[path] = self.reader.get(path)
        return self.held[path]

    def _document(self, path: str, held: bytes, day: date, key: str, status: str) -> None:
        """Receipt and manifest row of a file already in Drive, when the row is missing (same bytes: no-op in Drive)."""
        if not self.manifest.has(key, status, hashlib.sha256(held).hexdigest()):
            self._save(path, held, day, key, status)

    def _save(self, path: str, data: bytes, day: date, key: str, status: str) -> None:
        self.store.put(path, data)
        self.manifest.add(day, key, status, hashlib.sha256(data).hexdigest(), len(data))
