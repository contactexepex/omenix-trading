"""What the article writer would do with an article, decided from the Record alone (P2b2, and the staging cleanup).
One definition of the rule, read only:

- RECORDED: no file for this key yet.
- NO_OP: the Record holds the key with the same fixed fields (first_seen_at is not compared), in the article file or in
  the revision file of that version.
- REVISION: the key is held with different fixed fields (a live blog, a correction, or two items that share a key); the
  version goes to `news/revisions/<key[:2]>/<key>/<sha8>.json`, the sha8 being of the fixed fields, so the same version
  seen in many polls is kept once.

`ArticleWriter` acts on the plan; the staging cleanup asks it whether a staged poll's articles are already held."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum

from fno.ingestion.news.article.article_file import Article
from fno.ingestion.news.record.manifest import RECORDED, REVISION
from fno.ingestion.storage.raw_store import RawFileConflict, RawFileStore

ARTICLES, REVISIONS = "news/articles", "news/revisions"
UNCOMPARED = ("first_seen_at", "format", "wrapper_link")  # a redirect token may change between polls of one item


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


def _fields(data: bytes) -> dict | None:
    try:
        document = json.loads(data)
        return {k: v for k, v in document.items() if k not in UNCOMPARED} if isinstance(document, dict) else None
    except ValueError:
        return None


def same_version(held: bytes, new: bytes) -> bool:
    """Whether two article files say the same thing. They are compared on the fields BOTH carry, so an older file that
    lacks a field a newer format added is not a different article (without this every format 1 file would be written
    again as a "revision" the first time its article was seen again). Two files of one format differ in any field."""
    a, b = _fields(held), _fields(new)
    if a is None or b is None:
        return False  # a damaged file differs from every article
    shared = a.keys() & b.keys()
    return bool(shared) and all(a[k] == b[k] for k in shared)


@dataclass(frozen=True)
class Plan:
    outcome: Outcome
    path: str  # the Record file the outcome is about (the article file, or the revision file)
    status: str  # its manifest status
    held: bytes | None  # the bytes the Record already holds there (None: nothing yet)


class ArticlePlanner:
    def __init__(self, reader: RawFileStore):
        """`reader`: the Record area, for reading only."""
        self.reader = reader
        self.held: dict[str, bytes | None] = {}  # one Drive read per key per run, however many polls repeat it

    def plan(self, article: Article) -> Plan:
        path, data = article_path(article.key), article.to_bytes()
        held = self._held(path)
        if held is None:
            return Plan(Outcome.RECORDED, path, RECORDED, None)
        if same_version(held, data):
            return Plan(Outcome.NO_OP, path, RECORDED, held)
        sha8 = hashlib.sha256(_fixed(data) or b"").hexdigest()[:8]
        revision = f"{REVISIONS}/{article.key[:2]}/{article.key}/{sha8}.json"
        kept = self._held(revision)
        if kept is None:
            return Plan(Outcome.REVISION, revision, REVISION, None)
        if not same_version(kept, data):  # the same 8 hex characters for two versions: never called a no-op
            raise RawFileConflict(f"{revision}: revision name collision")
        return Plan(Outcome.NO_OP, revision, REVISION, kept)

    def _held(self, path: str) -> bytes | None:
        if path not in self.held:
            self.held[path] = self.reader.get(path)
        return self.held[path]
