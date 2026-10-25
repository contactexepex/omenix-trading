"""The day's v4 capture as the pack builder reads it (story G10 part 2, section 3): A4e's named 14:30-14:40 window,
dataset `quote-snapshots-v4`, read like every A4 reader (`fno/quotes/compare.py`): the canonical marker, then the
attempt's sidecar (repository) and its quote rows (Drive only, checked against the sidecar's SHA-256 by A4b's store)."""

from __future__ import annotations

import csv
import io
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date

from ..quotes.recorder import NONE_MARKER, QuoteSnapshotRecorder
from ..storage.raw_store import RawFileStore

MARKER, SIDECAR, QUOTES = "nifty_{day:%Y%m%d}.canonical", "{snapshot}.meta.json", "{snapshot}.csv"


@dataclass(frozen=True)
class V4Capture:
    dataset: str
    snapshot_id: str
    meta: dict
    rows: tuple[dict, ...]


class CaptureSource(ABC):
    @abstractmethod
    def capture(self, day: date) -> V4Capture | None:
        """The day's canonical capture; None when there is none (no marker, or the day ended "none")."""

    @abstractmethod
    def ended(self, day: date) -> bool:
        """Whether the day's capture has ended: its marker exists (canonical or "none"); nothing more will come."""


class StoredV4Capture(CaptureSource):
    def __init__(self, store: RawFileStore, dataset: str):
        self.store, self.dataset = store, dataset

    def capture(self, day: date) -> V4Capture | None:
        marker = self._get(day, MARKER.format(day=day))
        snapshot = marker.decode().strip() if marker else NONE_MARKER
        if snapshot == NONE_MARKER:
            return None
        meta, quotes = (
            self._get(day, SIDECAR.format(snapshot=snapshot)),
            self._get(day, QUOTES.format(snapshot=snapshot)),
        )
        if meta is None or quotes is None:
            return None
        rows = tuple(csv.DictReader(io.StringIO(quotes.decode("utf-8"))))
        return V4Capture(self.dataset, snapshot, json.loads(meta), rows)

    def ended(self, day: date) -> bool:
        return self._get(day, MARKER.format(day=day)) is not None

    def _get(self, day: date, name: str) -> bytes | None:
        return self.store.get(QuoteSnapshotRecorder.path(day, name, self.dataset))
