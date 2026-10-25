"""Gets a raw file from the cheapest place that has it. `RawFileLibrary` (a writer's): the stores first, then the
original source, keeping a copy of anything fetched. `StoredFilesLibrary` (a reader's): the stores only, so a file no
store holds is "not stored yet", never fetched or archived (one writer per dataset: its librarian job; 24 Oct 2026).
Both know only the interfaces, never a concrete store or source."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from .raw_source import RawFileSource
from .raw_store import RawFileStore

NOT_STORED = "not stored yet"  # a reader's library: no store holds the file (its librarian has not archived it)
NO_STORE = "no store to read {path} from: set the owner's Drive settings (or the service account's)"


class NoReadableStore(RuntimeError):
    """A reader's library has no store at all: "cannot read" must never look like "not archived yet" (DR1, 24 Oct)."""


@dataclass(frozen=True)
class RawFile:
    data: bytes | None  # None: the source does not publish this file
    origin: str  # the store or source it came from


class FileLibrary(ABC):
    @abstractmethod
    def get(self, path: str) -> RawFile:
        """The file at `path` and where it came from; `data` None when it is not available."""


class StoredFilesLibrary(FileLibrary):
    def __init__(self, stores: list[RawFileStore]):
        self.stores = stores

    def get(self, path: str) -> RawFile:
        if not self.stores:
            raise NoReadableStore(NO_STORE.format(path=path))
        for store in self.stores:
            data = store.get(path)
            if data is not None:
                return RawFile(data, store.name)
        return RawFile(None, NOT_STORED)


class RawFileLibrary(FileLibrary):
    def __init__(self, stores: list[RawFileStore], source: RawFileSource, archive: RawFileStore | None = None):
        self.stores, self.source, self.archive = stores, source, archive

    def get(self, path: str) -> RawFile:
        for store in self.stores:
            data = store.get(path)
            if data is not None:
                return RawFile(data, store.name)
        data = self.source.fetch(path)
        if data is not None and self.archive is not None:
            self.archive.put(path, data)  # RawFileConflict if a different file is there
        return RawFile(data, self.source.name)
