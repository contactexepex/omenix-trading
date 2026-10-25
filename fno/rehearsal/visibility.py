"""What the replay clock may see of the real Drive record (story REH1: no look-ahead). A file with an O9 receipt is
visible once its receipt's `written_at` is at or before the replay clock's now. The paper accounts' private files have
no receipts (they are index files, replaced in place): they are read as they are now, the one stated limit. A file
with a manifest row instead of a receipt (the A9 datasets, the global cues) is visible once the commit that added its
row is at or before now (REH1g). A Groww raw quote file, vouched for by its committed sidecar (A4b), is visible once
both its attempt's finish and its sidecar's commit are (REH1p). Any other file was never recorded as of the replay, so
it is not visible."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from ..storage.receipts import ReceiptFolder
from .manifest_rows import ManifestRows
from .quote_sidecars import QuoteSidecars

STATE_AREAS = ("paper/",)  # the private records E2c keeps in Drive (index files, no history)


class Visibility:
    def __init__(self, receipts: ReceiptFolder, now: Callable[[], datetime], rows: ManifestRows | None = None,
                 sidecars: QuoteSidecars | None = None):  # fmt: skip
        """`rows`: the manifests' committed rows, for the files that have a manifest row instead of a receipt;
        `sidecars`: the committed quote sidecars, for Groww's raw quote files."""
        self.receipts, self.now, self.rows, self.sidecars = receipts, now, rows, sidecars

    def __call__(self, path: str) -> bool:
        if path.startswith(STATE_AREAS):
            return True
        receipt = self.receipts.read(path)
        if receipt is not None:
            return datetime.fromisoformat(receipt.written_at) <= self.now()
        seen = self.rows.seen_at(path) if self.rows is not None else None
        if seen is None and self.sidecars is not None:
            seen = self.sidecars.seen_at(path)
        return seen is not None and seen <= self.now()
