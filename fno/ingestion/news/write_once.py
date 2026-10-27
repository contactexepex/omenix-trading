"""The write-once file writer of the news Record (P2d, generalised for NP2c): the only code that puts a derived news
file (a cluster file, a resolution file) into the Record. File first: the Drive file (then its receipt) and only then
the manifest row. The same bytes again is a no-op (a missing row is added from the held bytes); other bytes at the name
are a conflict, never an overwrite. `id_of` gives the manifest id of a path."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from datetime import date
from enum import Enum

from fno.ingestion.news.record.manifest import RECORDED, NewsManifest
from fno.ingestion.storage.data_store import DataStore
from fno.ingestion.storage.raw_store import RawFileConflict, RawFileStore


class Written(Enum):
    NEW = "written"
    UNCHANGED = "no_op"


class WriteOnceWriter:
    def __init__(self, reader: RawFileStore, store: DataStore, manifest: NewsManifest, id_of: Callable[[str], str]):
        """`reader`: the Record, read only; `store`: the write path (Drive, then receipt); `manifest`: this kind of
        file's own csv."""
        self.reader, self.store, self.manifest, self.id_of = reader, store, manifest, id_of

    @property
    def skipped_rows(self) -> int:
        return self.manifest.skipped

    def check_ready(self) -> None:
        """TableFileBroken when the manifest ends in a torn line: checked BEFORE any Drive file is written."""
        self.manifest.check_appendable()

    def write(self, path: str, data: bytes, day: date) -> Written:
        held = self.reader.get(path)
        if held is not None and held != data:
            raise RawFileConflict(f"{path}: the file exists with other bytes")
        outcome = Written.NEW if held is None else Written.UNCHANGED
        sha = hashlib.sha256(data).hexdigest()
        if held is None or not self.manifest.has(self.id_of(path), RECORDED, sha):
            self.store.put(path, data)
            self.manifest.add(day, self.id_of(path), RECORDED, sha, len(data))
        return outcome
