"""A receipt for a Drive data file that was saved but never receipted (story DR1-0): on 22 Oct run
20261022T100328Z-39767f's full run log reached Drive, but its receipt was lost when two runs raced. The receipt is
built from the file's own bytes and Drive's creation time; it is refused when the path has no file or more than one,
or already has a receipt (the existing receipt is the evidence and is never replaced)."""

from __future__ import annotations

import hashlib
from datetime import datetime

from .drive_items import DriveItems, PathAmbiguous, PathNotFound
from .raw_store import RawFileConflict
from .receipts import Receipt, ReceiptFolder

NO_FILE = "{path}: no file in Drive"
SEVERAL = "{path}: {count} files with this name in Drive; merge or choose first"
HAS_RECEIPT = "{path}: already has a receipt; it is never replaced"


class ReceiptRefused(RuntimeError):
    pass


class ReceiptRepair:
    def __init__(self, items: DriveItems, receipts: ReceiptFolder):
        self.items, self.receipts = items, receipts

    def receipt_for(self, path: str, writer: str, run_id: str) -> Receipt:
        """The receipt the file's bytes prove (nothing written)."""
        if self.receipts.read(path) is not None:
            raise ReceiptRefused(HAS_RECEIPT.format(path=path))
        try:
            _, copies = self.items.copies(path)
        except (PathNotFound, PathAmbiguous) as refusal:
            raise ReceiptRefused(str(refusal)) from refusal
        files = [item for item in copies if not item.folder]
        if not files:
            raise ReceiptRefused(NO_FILE.format(path=path))
        if len(files) > 1:
            raise ReceiptRefused(SEVERAL.format(path=path, count=len(files)))
        data = self.items.content(files[0])
        written_at = datetime.fromisoformat(files[0].created.replace("Z", "+00:00")).isoformat()
        return Receipt(path, hashlib.sha256(data).hexdigest(), len(data), written_at, writer, run_id)

    def write(self, receipt: Receipt) -> Receipt:
        try:
            return self.receipts.write(receipt)
        except RawFileConflict as conflict:
            raise ReceiptRefused(str(conflict)) from conflict
