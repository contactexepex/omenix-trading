"""Later versions of archived raw files (story A11): NSE sometimes rewrites a file after first publishing it (e.g.
`ind_close_all_12102026.csv`, rewritten at 23:20 IST on 12 Oct 2026 with two more indices). The raw file never
changes (A1); every later version found is saved in a separate `revisions` area under the same path, in a file named
by when that version became available and its SHA-256, and gets one row in an append-only index committed beside the
manifests. A row is never changed or removed; the same version found again changes nothing.

When a version became available: the source's Last-Modified for those bytes when it says one, else the time we
fetched them (an upper bound). Versions NSE published and replaced between two of our reads are never seen.
"""

from __future__ import annotations

import csv
import hashlib
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path, PurePosixPath

from ..models import IST, now_ist
from .manifest_folder import ManifestFolder, source_of
from .raw_source import NseArchiveSource, PublishedFile
from .raw_store import RawFileStore

INDEX_FIELDS = ("date", "path", "sha256", "size_bytes", "available_from", "last_modified", "found_at")
REVISION_NAME = "{at:%Y%m%dT%H%M%S%z}_{sha256}{suffix}"  # inside a folder named like the raw file's path


@dataclass(frozen=True)
class Revision:
    day: date
    path: str  # the raw file's archive path
    sha256: str
    size_bytes: int
    available_from: datetime  # the source's Last-Modified when it gave one, else found_at
    last_modified: datetime | None
    found_at: datetime

    @property
    def revision_path(self) -> str:
        """Where the bytes are, in the revisions area: the raw path, then the version's time and SHA-256."""
        suffix = "".join(PurePosixPath(self.path).suffixes)
        return f"{self.path}/{REVISION_NAME.format(at=self.available_from, sha256=self.sha256, suffix=suffix)}"


def _time(text: str) -> datetime | None:
    return datetime.fromisoformat(text) if text else None


class RevisionIndex:
    """One CSV per dataset (`<folder>/<dataset>.csv`), rows in the order the versions were found; append-only."""

    def __init__(self, folder: Path, sources: Iterable[type[NseArchiveSource]]):
        self.folder, self.sources = Path(folder), tuple(sources)

    def path_for(self, source: type[NseArchiveSource]) -> Path:
        return self.folder / f"{source.dataset.rsplit('/', 1)[-1]}.csv"

    def read(self, source: type[NseArchiveSource]) -> list[Revision]:
        file = self.path_for(source)
        if not file.is_file():
            return []
        return [
            Revision(
                date.fromisoformat(r["date"]),
                r["path"],
                r["sha256"],
                int(r["size_bytes"]),
                datetime.fromisoformat(r["available_from"]),
                _time(r["last_modified"]),
                datetime.fromisoformat(r["found_at"]),
            )
            for r in csv.DictReader(file.read_text(encoding="utf-8").splitlines())
        ]

    def for_path(self, path: str) -> list[Revision]:
        """The path's revisions, oldest version first."""
        found = [r for r in self.read(source_of(path, self.sources)) if r.path == path]
        return sorted(found, key=lambda r: (r.available_from, r.found_at))

    def append(self, source: type[NseArchiveSource], revision: Revision) -> None:
        self.folder.mkdir(parents=True, exist_ok=True)
        file = self.path_for(source)
        new = not file.is_file()
        with file.open("a", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, lineterminator="\n")
            if new:
                writer.writerow(INDEX_FIELDS)
            writer.writerow(_row(revision))

    def counts(self, source: type[NseArchiveSource]) -> dict[str, int]:
        """File name -> how many later versions are archived (for the coverage report)."""
        counts: dict[str, int] = {}
        for revision in self.read(source):
            name = revision.path.rsplit("/", 1)[-1]
            counts[name] = counts.get(name, 0) + 1
        return counts


def _row(r: Revision) -> list:
    stamp = r.last_modified.isoformat() if r.last_modified else ""
    return [
        r.day.isoformat(),
        r.path,
        r.sha256,
        r.size_bytes,
        r.available_from.isoformat(),
        stamp,
        r.found_at.isoformat(),
    ]


class RevisionArchive:
    """Saves a source's current bytes as a revision when they differ from the archived raw file and from every
    revision already indexed. Bytes for a path the raw archive does not hold are not a revision (the librarian
    archives them as the raw file) and are only noted."""

    def __init__(
        self,
        raw: RawFileStore,
        revisions: RawFileStore,
        index: RevisionIndex,
        manifests: ManifestFolder,
        clock: Callable[[], datetime] = now_ist,
    ):
        self.raw, self.revisions, self.index, self.manifests, self.clock = raw, revisions, index, manifests, clock
        self.stored: list[Revision] = []  # versions saved by this archive since it was made
        self.not_archived: list[str] = []  # paths offered with no raw file to compare with

    def capture(self, path: str, published: PublishedFile) -> Revision | None:
        """The new revision saved, or None when the bytes are a version already archived (or there is no raw file)."""
        source = source_of(path, self.index.sources)
        sha256 = hashlib.sha256(published.data).hexdigest()
        raw_sha256 = self._raw_sha256(source, path)
        if raw_sha256 is None:
            self.not_archived.append(path)
            return None
        if sha256 == raw_sha256 or sha256 in {r.sha256 for r in self.index.for_path(path)}:
            return None
        revision = self._revision(source, path, published, sha256)
        self.revisions.put(revision.revision_path, published.data)  # bytes first: a row always has its file
        self.index.append(source, revision)
        self.stored.append(revision)
        return revision

    def _raw_sha256(self, source: type[NseArchiveSource], path: str) -> str | None:
        fingerprint = self.manifests.fingerprints(source).get(path.rsplit("/", 1)[-1])
        if fingerprint is not None:
            return fingerprint
        data = self.raw.get(path)  # not fingerprinted yet: hash the archived bytes themselves
        return None if data is None else hashlib.sha256(data).hexdigest()

    def _revision(self, source, path: str, published: PublishedFile, sha256: str) -> Revision:
        found_at = self.clock()
        modified = published.last_modified.astimezone(IST) if published.last_modified else None
        day = source.day_for_path(path)
        return Revision(day, path, sha256, len(published.data), modified or found_at, modified, found_at)
