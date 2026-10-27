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
        """True only when the Record (or its revisions) provably holds this copy's exact bytes."""


class RevisionHolds(Protocol):
    def holds(self, path: str, sha256: str) -> bool:
        """Whether the revisions area has a version of `path` with this SHA-256."""


class KeepForever(PromotedProof):
    """No staged copy of this source is ever removed (a source with no cleanup rule yet)."""

    def promoted(self, copy: StagedCopy) -> bool:
        return False


class NseCopyProof(PromotedProof):
    """An NSE copy is promoted when the Record holds the SAME BYTES at its archive path (the promoted copy, or an exact
    duplicate of it), or the revisions area lists its SHA-256 for that path (a later version the gate kept). Then
    removing the staged copy loses nothing: the bytes are in the Record or in the revisions."""

    def __init__(self, record: RawFileStore, revisions: RevisionHolds):
        """`record`: the Record area, read only; `revisions`: the index of later versions, read only."""
        self.record, self.revisions = record, revisions

    def promoted(self, copy: StagedCopy) -> bool:
        digest = hashlib.sha256(copy.data).hexdigest()
        try:
            held = self.record.get(copy.path)
            return (held is not None and held == copy.data) or self.revisions.holds(copy.path, digest)
        except Exception:  # noqa: BLE001 - any doubt (Drive down, an unreadable index) keeps the copy
            return False
