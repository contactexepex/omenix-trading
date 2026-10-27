"""When a staged copy may be removed: only when it is PROVEN promoted, never because it is old (story S1). One
`PromotedProof` per source tag; a source with no proof keeps everything. Every proof answers False when it cannot
tell (a Drive error, an unreadable file), so a doubt keeps the copy."""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from typing import Protocol

from fno.ingestion.promotion.staging import StagedCopy
from fno.ingestion.storage.raw_store import RawFileStore


class PromotedProof(ABC):
    @abstractmethod
    def promoted(self, copy: StagedCopy) -> bool:
        """True only when the Record (or its revisions) provably holds this copy's exact bytes. May raise on any
        doubt it cannot settle (Drive down, a damaged index): the caller keeps the copy and counts the error."""


class RevisionHolds(Protocol):
    def holds(self, path: str, sha256: str) -> bool:
        """Whether the revisions area has a version of `path` with this SHA-256."""


class Fingerprints(Protocol):
    def sha256_of(self, path: str) -> str | None:
        """The SHA-256 the checkout's manifest records for the Record file at `path` (None: no row)."""


class NseCopyProof(PromotedProof):
    """An NSE copy is promoted when the Record holds the SAME BYTES at its archive path (the promoted copy, or an exact
    duplicate of it) AND the checkout's manifest holds the row for that file with the same SHA-256, or the revisions
    area lists its SHA-256 for that path (a later version the gate kept). The row matters: a stopped promote leaves a
    Record file without its row, and only a staged copy of the same bytes lets the gate write it later (judge 66 B1);
    removing that copy first would leave the file unfingerprinted for good. Then removing the staged copy
    loses nothing."""

    def __init__(self, record: RawFileStore, fingerprints: Fingerprints, revisions: RevisionHolds):
        """`record`: the Record area, read only; `fingerprints`: the manifest rows; `revisions`: later versions."""
        self.record, self.fingerprints, self.revisions = record, fingerprints, revisions

    def promoted(self, copy: StagedCopy) -> bool:
        digest = hashlib.sha256(copy.data).hexdigest()
        held = self.record.get(copy.path)  # a read error propagates: StagingCleanup keeps the copy and reports it
        if held is not None and held == copy.data:
            return self.fingerprints.sha256_of(copy.path) == digest
        return self.revisions.holds(copy.path, digest)
