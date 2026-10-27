"""The news manifest (P2b2): `research/data/manifests/news/articles.csv`, one row per Record file the gate wrote:
`date,article_id,status,sha256,size_bytes`. Hash ids only: no title, URL or feed. Written after Drive accepted the file
(file first, then receipt, then row), loaded once per run and appended to through `CsvRowLog`, never rewritten. A
recorded article id with a different SHA-256 is refused; a revision is one row per (article id, SHA-256).

A crash can leave a torn last line. The load skips and counts any row that is not whole (so the missing-row repair adds
it again), and an append refuses a file that does not end in a new line (`TableFileBroken`) rather than glue a row onto
the torn one: the owner trims the torn line by hand."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from fno.ingestion.news import codes
from fno.ingestion.storage.raw_store import RawFileConflict
from fno.ingestion.storage.row_log import CsvRowLog, TableFileBroken

FIELDS = ("date", "article_id", "status", "sha256", "size_bytes")
RECORDED, REVISION = "recorded", "revision"
FILE_NAME = "articles.csv"
HEX64 = re.compile(r"[0-9a-f]{64}")  # an article id and a SHA-256 are both 64 hex characters


def _whole(row: dict) -> bool:
    cells = [row.get(field) for field in FIELDS]
    return (
        all(cell for cell in cells)
        and None not in row  # extra cells land under the key None
        and row["status"] in (RECORDED, REVISION)
        and bool(HEX64.fullmatch(row["article_id"]))
        and bool(HEX64.fullmatch(row["sha256"]))
        and row["size_bytes"].isdigit()
    )


class NewsManifest:
    def __init__(self, folder: Path, file_name: str = FILE_NAME):
        self.log = CsvRowLog(Path(folder) / file_name)
        rows = self.log.rows()
        whole = [r for r in rows if _whole(r)]
        self.skipped = len(rows) - len(whole)  # rows that are not whole: reported by the gate, never silently dropped
        self.rows: set[tuple[str, str, str]] = {(r["article_id"], r["status"], r["sha256"]) for r in whole}
        self.recorded: dict[str, str] = {r["article_id"]: r["sha256"] for r in whole if r["status"] == RECORDED}

    def problem(self) -> str | None:
        """The fixed code of what makes the file unsafe to commit, or None when whole: a last line with no new line
        (even a complete row) or rows that are not whole. Each is checked on its own."""
        try:
            self.check_appendable()
        except TableFileBroken:
            return codes.MANIFEST_BROKEN
        return codes.MANIFEST_ROW_SKIPPED if self.skipped else None

    def well_formed(self) -> bool:
        return self.problem() is None

    def check_appendable(self) -> None:
        """TableFileBroken when the file ends in a torn line (checked before anything is written)."""
        self.log.check_appendable()

    def has(self, article_id: str, status: str, sha256: str) -> bool:
        return (article_id, status, sha256) in self.rows

    def add(self, day: date, article_id: str, status: str, sha256: str, size: int) -> None:
        """The same row again changes nothing; a recorded id with another SHA-256 is a conflict."""
        if self.has(article_id, status, sha256):
            return
        if status == RECORDED and self.recorded.get(article_id, sha256) != sha256:
            raise RawFileConflict("the news manifest already has a different SHA-256 for this article id")
        self.check_appendable()
        self.log.append(FIELDS, [(day.isoformat(), article_id, status, sha256, size)])
        self.rows.add((article_id, status, sha256))
        if status == RECORDED:
            self.recorded[article_id] = sha256
