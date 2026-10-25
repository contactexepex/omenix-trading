"""The real record, read-only (story REH1b): what a recorded source replays from. Reads only; any write raises
before it reaches the store, so a recorded source can never change what it replays."""

from __future__ import annotations

from ..quotes.drive_only_store import DriveOnlyQuoteStore
from ..storage.raw_store import RawFileStore
from .drive import WRITE_REFUSED, RehearsalWriteRefused


class RecordReader(RawFileStore):
    def __init__(self, inner: RawFileStore):
        self.inner = inner
        self.name = f"{getattr(inner, 'name', 'store')} (the real record, read-only)"

    def get(self, path: str) -> bytes | None:
        return self.inner.get(path)

    def checksums(self, folder: str) -> dict[str, str]:
        return self.inner.checksums(folder)

    def folders(self, folder: str) -> list[str]:
        return self.inner.folders(folder)

    def put(self, path: str, data: bytes) -> None:
        raise RehearsalWriteRefused(WRITE_REFUSED.format(what="write of", path=path, root="dryrun/<run_id>"))


class ListedQuoteRecord(DriveOnlyQuoteStore):
    """The day's 3 pm record as A4b keeps it (sidecars and markers in the repository, raw quote files in Drive only),
    listed by folder: the recorded recorder finds the day's attempts from their sidecars (REH1g, DRY2's crash). The
    listing is the repository's; a raw quote file is read by name, checked against its sidecar as ever."""

    def checksums(self, folder: str) -> dict[str, str]:
        return self.repository.checksums(folder)

    def folders(self, folder: str) -> list[str]:
        return self.repository.folders(folder)
