"""A store opened at its first use (story E2c's pattern for Drive): building the daily run needs no Drive, and a run
before E8's live date never signs in for it; missing Drive settings then stop only the step that needed them."""

from __future__ import annotations

from collections.abc import Callable

from ...storage.raw_store import RawFileStore


class OpenedOnFirstUse(RawFileStore):
    def __init__(self, name: str, open_store: Callable[[], RawFileStore]):
        self.name, self._open, self._store = name, open_store, None

    def store(self) -> RawFileStore:
        if self._store is None:
            self._store = self._open()
        return self._store

    def get(self, path: str) -> bytes | None:
        return self.store().get(path)

    def put(self, path: str, data: bytes) -> None:
        self.store().put(path, data)

    def checksums(self, folder: str) -> dict[str, str]:
        return self.store().checksums(folder)

    def folders(self, folder: str) -> list[str]:
        return self.store().folders(folder)
