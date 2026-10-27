"""The wrapper index (NP2d): `research/data/manifests/news/wrappers.csv`, one row for each recorded Google News article
that has a redirect link to resolve, in the news manifest's own layout (`date,article_id,status,sha256,size_bytes`; hash
ids only). The gate adds the row when it records the article, so the resolve pass (NP2c) and the page-read pass (NP4) go
straight to the articles they need instead of reading every article of the look-back to find them (the articles
manifest cannot say which article is which kind). It is an index of the Record, not a Record file: nothing in Drive, no
receipt of its own. Adding a row is idempotent, so a run killed between the article row and this row is repaired by the
next promote of the same poll."""

from __future__ import annotations

import hashlib
from datetime import date
from pathlib import Path

from fno.ingestion.news.article.article_file import Article
from fno.ingestion.news.article.keys import WRAPPER
from fno.ingestion.news.record.manifest import RECORDED, NewsManifest

WRAPPERS_FILE = "wrappers.csv"


def is_resolvable(article: Article) -> bool:
    return article.kind == WRAPPER and bool(article.wrapper_link)


class WrapperIndex:
    def __init__(self, folder: Path):
        self.manifest = NewsManifest(folder, WRAPPERS_FILE)

    @property
    def skipped(self) -> int:
        return self.manifest.skipped

    def check_appendable(self) -> None:
        self.manifest.check_appendable()

    def mark(self, day: date, article: Article, recorded_bytes: bytes) -> None:
        """`recorded_bytes`: the article file the Record holds (the first version, never a revision)."""
        if is_resolvable(article):
            sha = hashlib.sha256(recorded_bytes).hexdigest()
            self.manifest.add(day, article.key, RECORDED, sha, len(recorded_bytes))
