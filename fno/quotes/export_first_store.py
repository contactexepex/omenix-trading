"""The quote store a replay reads (story A4b, judge 111 addendum 2): a commit's exported files first, each file on its
own; a quote file the export does not hold is read from the Drive-only store, checked against its committed sidecar.

A file in the export is used as it is: `git archive` gives exactly the committed bytes (git addresses objects by their
own hash), so no second check is needed there. Deciding per file, not per tree, keeps a mixed export right: a commit
that still holds an older day's quote file and a later day's sidecar only reads the later day from Drive, never
quietly from nowhere (which the frozen capture would take as "no Groww snapshot" and switch to NSE's).
"""

from __future__ import annotations

from ..storage.raw_store import RawFileStore, ReadOnlyStoreError


class ExportFirstQuoteStore(RawFileStore):
    def __init__(self, export: RawFileStore, drive_only: RawFileStore):
        self.export, self.drive_only = export, drive_only
        self.name = f"{export.name}, then {drive_only.name}"

    def get(self, path: str) -> bytes | None:
        data = self.export.get(path)
        return data if data is not None else self.drive_only.get(path)

    def put(self, path: str, data: bytes) -> None:
        raise ReadOnlyStoreError("a replay never writes quote files")
