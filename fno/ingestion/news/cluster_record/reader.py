"""Reading clusters "as known at T" (P2d; design N10). The newest file holds only its window, so a reader takes the
latest file with a window end at or before T WHOSE WINDOW COVERS the story's effective time: a story older than the
newest file's window is still reached through an earlier file. Read only; nothing here can write.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from fno.ingestion.news.cluster_record.cluster_file import (
    ClusterFile,
    cluster_folder,
    parse_cluster_file,
    window_end_of,
)
from fno.ingestion.storage.raw_store import RawFileStore


class ClusterReader:
    def __init__(self, record: RawFileStore, version: str):
        self.record, self.version = record, version

    def as_known_at(self, known_at: datetime, effective: datetime) -> ClusterFile | None:
        """The latest file with window end <= `known_at` whose window contains `effective`, or None."""
        folder = cluster_folder(self.version)
        ends = sorted(
            ((end, name) for name in self.record.checksums(folder) if (end := window_end_of(name)) and end <= known_at),
            reverse=True,
        )
        for end, name in ends:
            data = self.record.get(f"{folder}/{name}")
            if data is None:
                continue
            found = parse_cluster_file(data)
            if end - timedelta(hours=found.window_hours) <= effective <= end:
                return found
        return None
