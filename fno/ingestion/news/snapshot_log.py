"""The repository's only record of a news poll (P2, N1): one row per staged poll (when, which feed by its opaque id,
the Staging path, the SHA-256 and size of the raw bytes, the feed-list version) and one row per feed-list version
ever used (its SHA-256). Never a URL, a query or a form field. A poll row is written after Staging accepted the
bytes, so it always describes a poll that is in Drive. The list's hash is salted (the list format requires a random
salt), so it cannot confirm a guessed list."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from fno.ingestion.storage.row_log import CsvRowLog

FIELDS = ("fetched_at", "feed_id", "path", "sha256", "size_bytes", "feed_list_version")
LIST_FIELDS = ("first_used_at", "feed_list_version", "feed_list_sha256")
LOG_FILE, LISTS_FILE = "polls.csv", "feed_lists.csv"


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
        self.lists = CsvRowLog(Path(folder) / LISTS_FILE)  # one row per feed-list version ever used

    def append(self, row: PollRow) -> None:
        self.log.check_appendable()
        cells = (row.fetched_at.isoformat(), row.feed_id, row.path, row.sha256, row.size_bytes, row.feed_list_version)
        self.log.append(FIELDS, [cells])

    def note_feed_list(self, version: int, sha256: str, at: datetime) -> None:
        """Records that this version (with this hash) is in use, once per version: a run of unchanged polls still
        leaves the record and the file stays tiny. Written before the first request that uses it."""
        if version not in self.used_feed_lists():
            self.lists.check_appendable()
            self.lists.append(LIST_FIELDS, [(at.isoformat(), version, sha256)])

    def highest_feed_list_version(self) -> int:
        return max(self.used_feed_lists(), default=0)

    def used_feed_lists(self) -> dict[int, str]:
        """Version -> the SHA-256 it had when first used (hashes only)."""
        return {int(r["feed_list_version"]): r["feed_list_sha256"] for r in self.lists.rows()}
