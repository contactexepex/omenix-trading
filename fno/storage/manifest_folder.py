"""The SHA-256 manifests of the raw archive (stories A9, A10): one CSV per dataset in one folder of the repository,
written by one code path: whole from the archive (`fingerprints.py`), and one row whenever a file is saved
(`FingerprintingStore`). The coverage check reads them; a file without a row is reported as unfingerprinted.

Columns `date,url,status,sha256,size_bytes`, one row per archived file (status always 200), sorted by date. A row is
never changed: a different SHA-256 for a day that already has one is refused.
"""

from __future__ import annotations

import csv
import hashlib
import io
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .raw_source import NseArchiveSource
from .raw_store import RawFileConflict, RawFileStore

MANIFEST_FIELDS = ("date", "url", "status", "sha256", "size_bytes")
PUBLISHED = "200"


@dataclass(frozen=True)
class Fingerprint:
    day: date
    url: str
    sha256: str
    size_bytes: int

    @classmethod
    def of(cls, source: type[NseArchiveSource], path: str, data: bytes) -> Fingerprint:
        day = source.day_for_path(path)
        return cls(day, source.url_for(path), hashlib.sha256(data).hexdigest(), len(data))

    @property
    def filename(self) -> str:
        return self.url.rsplit("/", 1)[-1]


class ManifestFolder:
    def __init__(self, folder: Path):
        self.folder = Path(folder)

    def path_for(self, source: type[NseArchiveSource]) -> Path:
        return self.folder / f"{source.dataset.rsplit('/', 1)[-1]}.csv"

    def read(self, source: type[NseArchiveSource]) -> list[Fingerprint]:
        path = self.path_for(source)
        if not path.is_file():
            return []
        rows = csv.DictReader(path.read_text(encoding="utf-8").splitlines())
        return [
            Fingerprint(date.fromisoformat(r["date"]), r["url"], r["sha256"], int(r["size_bytes"]))
            for r in rows
            if r["status"] == PUBLISHED
        ]

    def fingerprints(self, source: type[NseArchiveSource]) -> dict[str, str]:
        """File name -> SHA-256, what the coverage check and the librarian verify against."""
        return {f.filename: f.sha256 for f in self.read(source)}

    def write(self, source: type[NseArchiveSource], fingerprints: Iterable[Fingerprint]) -> None:
        self.folder.mkdir(parents=True, exist_ok=True)
        path = self.path_for(source)
        temporary = path.with_name(f".{path.name}.part")
        temporary.write_text(manifest_text(fingerprints), encoding="utf-8")
        temporary.replace(path)  # never a half-written manifest

    def record(self, source: type[NseArchiveSource], fingerprint: Fingerprint) -> None:
        """Adds one file's row (a file is its day and URL: one per day for a dated file or a daily copy, one per symbol
        and day for a symbol's own list); the same row again changes nothing, a different SHA-256 is refused."""
        rows = {(f.day, f.url): f for f in self.read(source)}
        key = (fingerprint.day, fingerprint.url)
        existing = rows.get(key)
        if existing == fingerprint:
            return
        if existing is not None:
            raise RawFileConflict(f"{fingerprint.filename}: the manifest already has a different SHA-256")
        rows[key] = fingerprint
        self.write(source, rows.values())


def manifest_text(fingerprints: Iterable[Fingerprint]) -> str:
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(MANIFEST_FIELDS)
    rows = sorted(fingerprints, key=lambda f: (f.day, f.url))
    writer.writerows((f.day.isoformat(), f.url, PUBLISHED, f.sha256, f.size_bytes) for f in rows)
    return out.getvalue()


class FingerprintingStore(RawFileStore):
    """Wraps the archive: every file it saves gets its manifest row in the same operation (after the store accepted
    it, so a row always describes bytes the archive holds). Reads pass straight through."""

    def __init__(self, store: RawFileStore, manifests: ManifestFolder, sources: Iterable[type[NseArchiveSource]]):
        self.store, self.manifests, self.sources = store, manifests, tuple(sources)
        self.name = store.name

    def get(self, path: str) -> bytes | None:
        return self.store.get(path)

    def put(self, path: str, data: bytes) -> None:
        source = source_of(path, self.sources)
        self.store.put(path, data)
        self.manifests.record(source, Fingerprint.of(source, path, data))


def source_of(path: str, sources: Iterable[type[NseArchiveSource]]) -> type[NseArchiveSource]:
    """The dataset an archive path belongs to (ValueError when none has a manifest: nobody could verify the file)."""
    for source in sources:
        if path.startswith(f"{source.dataset}/"):
            return source
    raise ValueError(f"{path}: no dataset with a manifest; refusing to save a file nobody can verify")
