"""Groww's candle answers kept raw in the owner's Drive (story A16b): one gzip JSON document per answer (no time in the
gzip header, so the same answer always gives the same bytes), under its own content-addressed name, so nothing is
ever written over and a later answer with other bytes sits beside the first. Each copy has a row in the repository's
manifest, one per kind (`research/data/manifests/groww-candles/nifty-15m.csv` and `nifty-1m.csv`: path, window,
times, SHA-256, size; never a price). The same bytes fetched again keep their first row and first fetch time."""

from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from ..storage.raw_store import RawFileStore
from .candle_source import FIFTEEN_MINUTES, ONE_MINUTE, CandleAnswer

FOLDER = "groww/indices/nifty-candles-{kind}/{start:%Y}"
NAME = "nifty_{kind}_{start:%Y%m%d}_{end:%Y%m%d}_{sha:.16}.json.gz"
MANIFEST = "nifty-{kind}.csv"
KINDS = (FIFTEEN_MINUTES, ONE_MINUTE)
FIELDS = ("kind", "start", "end", "path", "sha256", "size", "requested_at", "fetched_at")


class CopyDamaged(ValueError):
    """A copy is missing from Drive or its bytes differ from its manifest row."""


@dataclass(frozen=True)
class ArchivedCopy:
    kind: str
    start: date
    end: date
    path: str
    sha256: str
    fetched_at: datetime
    rows: list  # Groww's candle rows


class CandleArchive:
    def __init__(self, store: RawFileStore, manifest_folder: Path):
        self.store, self.manifest_folder = store, Path(manifest_folder)

    def save(self, answer: CandleAnswer) -> ArchivedCopy:
        """Drive first, then the manifest row: a row always describes bytes Drive holds. Bytes already held keep their
        first row, so the copy's fetch time is the first one (a rerun never moves `first_seen_at`)."""
        data = gzip.compress(answer.raw, mtime=0)
        sha256 = hashlib.sha256(data).hexdigest()
        folder = FOLDER.format(kind=answer.kind, start=answer.start)
        path = f"{folder}/{NAME.format(kind=answer.kind, start=answer.start, end=answer.end, sha=sha256)}"
        self.store.put(path, data)
        held = self.row_for(path)
        if held is None:
            self._append(answer, path, sha256, len(data))
        fetched = datetime.fromisoformat(held["fetched_at"]) if held else answer.received_at
        return ArchivedCopy(answer.kind, answer.start, answer.end, path, sha256, fetched, answer.rows)

    def manifest(self, kind: str) -> Path:
        return self.manifest_folder / MANIFEST.format(kind=kind)

    def rows(self) -> list[dict[str, str]]:
        found = []
        for kind in KINDS:
            if self.manifest(kind).is_file():
                found += csv.DictReader(io.StringIO(self.manifest(kind).read_text(encoding="utf-8")))
        return found

    def copies(self, kind: str, start: date, end: date) -> list[ArchivedCopy]:
        """Every copy of `kind` whose window overlaps start..end, earliest fetched first."""
        first, last = start.isoformat(), end.isoformat()
        held = [r for r in self.rows() if r["kind"] == kind and r["start"] <= last and r["end"] >= first]
        return [self.load(r) for r in sorted(held, key=lambda r: r["fetched_at"])]

    def load(self, row: dict[str, str]) -> ArchivedCopy:
        data = self.store.get(row["path"])
        if data is None:
            raise CopyDamaged(f"{row['path']}: not in Drive")
        if hashlib.sha256(data).hexdigest() != row["sha256"]:
            raise CopyDamaged(f"{row['path']}: SHA-256 differs from its manifest row")
        rows = json.loads(gzip.decompress(data))["candles"]
        start, end = date.fromisoformat(row["start"]), date.fromisoformat(row["end"])
        fetched = datetime.fromisoformat(row["fetched_at"])
        return ArchivedCopy(row["kind"], start, end, row["path"], row["sha256"], fetched, rows)

    def row_for(self, path: str) -> dict[str, str] | None:
        return next((r for r in self.rows() if r["path"] == path), None)

    def _append(self, answer: CandleAnswer, path: str, sha256: str, size: int) -> None:
        manifest = self.manifest(answer.kind)
        new = not manifest.is_file() or not manifest.stat().st_size
        manifest.parent.mkdir(parents=True, exist_ok=True)
        with manifest.open("a", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, lineterminator="\n")
            if new:
                writer.writerow(FIELDS)
            times = answer.requested_at.isoformat(), answer.received_at.isoformat()
            writer.writerow([answer.kind, answer.start.isoformat(), answer.end.isoformat(), path, sha256, size, *times])
