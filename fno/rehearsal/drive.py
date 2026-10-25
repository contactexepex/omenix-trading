"""The rehearsal's owner Drive: every write lands under `dryrun/<run_id>/`, write-once as ever; the real record is
read through it but never written. A read looks in the rehearsal's own folder first (what an earlier step of the same
rehearsal wrote), then in the real root, but only for a file the replay clock may see (`Visibility`). An index file's
in-place replace is allowed only for an ID this store found or made under its own folder."""

from __future__ import annotations

from collections.abc import Callable

from ..storage.raw_store import RawFileStore

WRITE_REFUSED = "rehearsal: no write to the real Drive record ({what} {path}); every write goes under {root}/"


class RehearsalWriteRefused(RuntimeError):
    """A rehearsal tried to write outside `dryrun/<run_id>/`: refused before any request is made."""


class DryrunDrive(RawFileStore):
    name = "rehearsal drive"

    def __init__(self, real, root: str, visible: Callable[[str], bool]):
        self.real, self.root, self.visible = real, root.rstrip("/"), visible
        self._mine: set[str] = set()

    def _own(self, path: str) -> str:
        return f"{self.root}/{path.lstrip('/')}"

    def get(self, path: str) -> bytes | None:
        data = self.real.get(self._own(path))
        if data is not None:
            return data
        return self.real.get(path) if self.visible(path) else None

    def put(self, path: str, data: bytes) -> None:
        self.real.put(self._own(path), data)

    def file_id(self, path: str) -> str | None:
        """Only the rehearsal's own copy: a real file's ID is never handed out, so it can never be replaced."""
        found = self.real.file_id(self._own(path))
        if found is not None:
            self._mine.add(found)
        return found

    def replace_contents(self, file_id: str, data: bytes) -> None:
        if file_id not in self._mine:
            raise RehearsalWriteRefused(WRITE_REFUSED.format(what="replace of", path=file_id, root=self.root))
        self.real.replace_contents(file_id, data)

    def checksums(self, folder: str) -> dict[str, str]:
        real = {name: md5 for name, md5 in self.real.checksums(folder).items() if self.visible(f"{folder}/{name}")}
        return real | self.real.checksums(self._own(folder))

    def folders(self, folder: str) -> list[str]:
        return sorted(set(self.real.folders(folder)) | set(self.real.folders(self._own(folder))))

    def metadata(self, path: str, fields: str) -> dict | None:
        own = self.real.metadata(self._own(path), fields)
        if own is not None:
            return own
        return self.real.metadata(path, fields) if self.visible(path) else None

    def root_listing(self) -> tuple[str, list[str]]:
        return self.real.root_listing()

    def record_view(self):
        """The real record, read-only: what a recorded source replays from (REH1b)."""
        from .record_store import RecordReader

        return RecordReader(self.real)
