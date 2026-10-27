"""Write-once versioned files in the private config area of Drive (P2 for the feed list, NP3 for the others):
`<prefix>-v<N>.json`, never edited in place, the owner adds a version instead. One definition of how the newest is
chosen, so the feed list, the company list and the discovery config cannot drift apart:

- the newest version by number is used; none at all is `missing`;
- a newest version older than one already used is `rolled_back` (no going back by deleting a file);
- a version whose SHA-256 differs from what it had when it was used was edited in place: it is skipped, never silently
  (it is named in `damaged`) and the next older good one is used; when none is left that is `damaged`.

The bytes are returned, not parsed: what a file means is the caller's. Errors are fixed codes of the caller's own."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from dataclasses import dataclass

from fno.ingestion.storage.raw_store import RawFileStore


@dataclass(frozen=True)
class ErrorCodes:
    missing: str
    rolled_back: str
    damaged: str


@dataclass(frozen=True)
class Picked:
    version: int
    data: bytes
    sha256: str
    damaged: tuple[int, ...] = ()  # newer versions skipped because they were edited after use


class VersionedFiles:
    def __init__(self, store: RawFileStore, folder: str, prefix: str, codes: ErrorCodes, error: type[Exception]):
        """`store`: the private config area (read only here); `error`: raised with one of `codes`, never with a text."""
        self.store, self.folder, self.codes, self.error = store, folder, codes, error
        self.pattern = re.compile(rf"^{re.escape(prefix)}-v(\d+)\.json$")

    def versions(self) -> dict[int, str]:
        return {int(m.group(1)): n for n in self.store.checksums(self.folder) if (m := self.pattern.match(n))}

    def read(self, version: int) -> bytes | None:
        name = self.versions().get(version)
        return self.store.get(f"{self.folder}/{name}") if name else None

    def latest(self, lowest_version: int = 0, used: Mapping[int, str] | None = None) -> Picked:
        """`lowest_version`: the newest already used, below which the run stops. `used`: the SHA-256 each used
        version had when it was used."""
        used = used or {}
        versions = self.versions()
        if not versions:
            raise self.error(self.codes.missing)
        if max(versions) < lowest_version:
            raise self.error(self.codes.rolled_back)
        damaged = []
        for version in sorted(versions, reverse=True):
            data = self.store.get(f"{self.folder}/{versions[version]}")
            if data is None:
                raise self.error(self.codes.missing)
            digest = hashlib.sha256(data).hexdigest()
            if version in used and digest != used[version]:
                damaged.append(version)
                continue
            return Picked(version, data, digest, tuple(damaged))
        raise self.error(self.codes.damaged)

    def every_version(self) -> list[tuple[int, bytes | None]]:
        """(version, bytes) oldest first; None for a file that could not be read."""
        return [(v, self.store.get(f"{self.folder}/{n}")) for v, n in sorted(self.versions().items())]
