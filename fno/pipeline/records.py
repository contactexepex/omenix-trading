"""The pipeline's write-once records in Drive (story O6): "fired" (the download job started the routine for this
batch and version) and "processed" (the routine finished it). One small JSON file per routine, batch and version,
in the store's `fired/` and `processed/` folders; the store's own rule makes them write-once (the same bytes again
is a no-op, different bytes are refused) and nothing is ever deleted."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime

from ..storage.raw_store import RawFileStore
from .pointer import BatchPointer

FIRED, PROCESSED = "fired", "processed"


class PipelineRecords:
    def __init__(self, store: RawFileStore, clock: Callable[[], datetime]):
        self.store, self.clock = store, clock

    @staticmethod
    def _path(kind: str, routine: str, pointer: BatchPointer) -> str:
        return f"{kind}/{routine}/{pointer.key}"

    def has(self, kind: str, routine: str, pointer: BatchPointer) -> bool:
        return self.store.get(self._path(kind, routine, pointer)) is not None

    def mark(self, kind: str, routine: str, pointer: BatchPointer, **details: str) -> None:
        record = {"at": self.clock().isoformat(timespec="seconds"), "pointer": pointer.to_text(), **details}
        self.store.put(self._path(kind, routine, pointer), json.dumps(record, sort_keys=True).encode())
