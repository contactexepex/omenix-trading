"""The cluster file writer (P2d): the only code that puts a cluster file into the Record. Write-once, file first: the
Drive file (then its receipt) and only then the manifest row. The same bytes again is a no-op (a missing row is added
from the held bytes); other bytes at the name are a conflict, never an overwrite. A closed window clusters to stable
bytes, so a conflict means the inputs, the algorithm version or the determinism changed for that window: investigate.
"""

from __future__ import annotations

import hashlib
from datetime import date
from enum import Enum

from fno.ingestion.news.cluster_record.cluster_file import path_id
from fno.ingestion.news.record.manifest import RECORDED, NewsManifest
from fno.ingestion.storage.data_store import DataStore
from fno.ingestion.storage.raw_store import RawFileConflict, RawFileStore


class Written(Enum):
    NEW = "written"
    UNCHANGED = "no_op"


class ClusterWriter:
    def __init__(self, reader: RawFileStore, store: DataStore, manifest: NewsManifest):
        """`reader`: the Record, read only; `store`: the write path (Drive, then receipt); `manifest`: clusters.csv."""
        self.reader, self.store, self.manifest = reader, store, manifest

    @property
    def skipped_rows(self) -> int:
        return self.manifest.skipped

    def check_ready(self) -> None:
        """TableFileBroken when clusters.csv ends in a torn line: checked BEFORE the Drive file is written."""
        self.manifest.check_appendable()

    def write(self, path: str, data: bytes, day: date) -> Written:
        held = self.reader.get(path)
        if held is not None and held != data:
            raise RawFileConflict(f"{path}: the file exists with other bytes")
        outcome = Written.NEW if held is None else Written.UNCHANGED
        sha = hashlib.sha256(data).hexdigest()
        if held is None or not self.manifest.has(path_id(path), RECORDED, sha):
            self.store.put(path, data)
            self.manifest.add(day, path_id(path), RECORDED, sha, len(data))
        return outcome
