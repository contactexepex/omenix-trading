"""The news manifest (P2b2): `research/data/manifests/news/articles.csv`, one row per Record file the gate wrote:
`date,article_id,status,sha256,size_bytes`. Hash ids only: no title, URL or feed. Written after Drive accepted the file
(file first, then receipt, then row), loaded once per run and appended to, never rewritten. A recorded article id with
a different SHA-256 is refused; a revision is one row per (article id, SHA-256)."""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from fno.ingestion.storage.raw_store import RawFileConflict

FIELDS = ("date", "article_id", "status", "sha256", "size_bytes")
RECORDED, REVISION = "recorded", "revision"
FILE_NAME = "articles.csv"


class NewsManifest:
    def __init__(self, folder: Path):
        self.path = Path(folder) / FILE_NAME
        rows = list(csv.DictReader(self.path.read_text(encoding="utf-8").splitlines())) if self.path.is_file() else []
        self.rows: set[tuple[str, str, str]] = {(r["article_id"], r["status"], r["sha256"]) for r in rows}
        self.recorded: dict[str, str] = {r["article_id"]: r["sha256"] for r in rows if r["status"] == RECORDED}

    def has(self, article_id: str, status: str, sha256: str) -> bool:
        return (article_id, status, sha256) in self.rows

    def add(self, day: date, article_id: str, status: str, sha256: str, size: int) -> None:
        """The same row again changes nothing; a recorded id with another SHA-256 is a conflict."""
        if self.has(article_id, status, sha256):
            return
        if status == RECORDED and self.recorded.get(article_id, sha256) != sha256:
            raise RawFileConflict("the news manifest already has a different SHA-256 for this article id")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fresh = not self.path.is_file()
        with self.path.open("a", encoding="utf-8", newline="") as out:
            writer = csv.writer(out, lineterminator="\n")
            if fresh:
                writer.writerow(FIELDS)
            writer.writerow((day.isoformat(), article_id, status, sha256, size))
        self.rows.add((article_id, status, sha256))
        if status == RECORDED:
            self.recorded[article_id] = sha256
