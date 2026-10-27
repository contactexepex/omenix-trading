"""One row per staged poll (P2, N1): when, which feed (its opaque id), the Staging path, the SHA-256 and size of the
raw bytes, and the feed-list version used. Never a URL, a query or a form field. Written after Staging accepted the
bytes, so a row always describes a poll that is in Drive. The highest version used is read back from here (no
rolling back)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from fno.ingestion.storage.row_log import CsvRowLog

FIELDS = ("fetched_at", "feed_id", "path", "sha256", "size_bytes", "feed_list_version")
LOG_FILE = "polls.csv"


@dataclass(frozen=True)
class PollRow:
    fetched_at: datetime
    feed_id: str
    path: str
    sha256: str
    size_bytes: int
    feed_list_version: int


class NewsSnapshotLog:
    def __init__(self, folder: Path):
        self.log = CsvRowLog(Path(folder) / LOG_FILE)

    def append(self, row: PollRow) -> None:
        self.log.check_appendable()
        cells = (row.fetched_at.isoformat(), row.feed_id, row.path, row.sha256, row.size_bytes, row.feed_list_version)
        self.log.append(FIELDS, [cells])

    def highest_feed_list_version(self) -> int:
        return max((int(r["feed_list_version"]) for r in self.log.rows()), default=0)
