"""Reads the right version of a raw file (story A11): the raw archive plus its revisions, behind `RawFileStore`, so
every reader of raw files (the library, the panel builder, the read models) can use it unchanged.

- point in time (`as_of` set): the newest version available at that moment, for research (no look-ahead: a version
  NSE wrote after the decision time is never returned);
- latest (`as_of` None): NSE's newest version we hold, for publishing.

Which day's file a decision may use at all is the availability rule's question (A8), not this reader's. Read-only.
"""

from __future__ import annotations

import hashlib
from datetime import datetime

from .raw_store import RawFileStore, ReadOnlyStoreError, StoredCopyDamaged
from .revisions import Revision, RevisionIndex


class VersionedRawStore(RawFileStore):
    def __init__(self, raw: RawFileStore, revisions: RawFileStore, index: RevisionIndex, as_of: datetime | None):
        self.raw, self.revisions, self.index, self.as_of = raw, revisions, index, as_of
        self.name = raw.name if as_of is None else f"{raw.name} as of {as_of:%Y-%m-%d %H:%M %Z}"

    def get(self, path: str) -> bytes | None:
        revision = self.version(path)
        return self.raw.get(path) if revision is None else self._read(revision)

    def version(self, path: str) -> Revision | None:
        """The revision this reader returns for the path; None means the raw file (no later version applies)."""
        found = [r for r in self.index.for_path(path) if self.as_of is None or r.available_from <= self.as_of]
        return found[-1] if found else None

    def put(self, path: str, data: bytes) -> None:
        raise ReadOnlyStoreError("a versioned reader never writes; archive revisions through RevisionArchive")

    def _read(self, revision: Revision) -> bytes:
        data = self.revisions.get(revision.revision_path)
        if data is None or hashlib.sha256(data).hexdigest() != revision.sha256:
            raise StoredCopyDamaged(f"{revision.revision_path}: missing or not the indexed SHA-256")
        return data
