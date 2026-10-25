"""The only way a job saves a data file (story O9, rules 1-3): the bytes go write-once into one area of the owner's
Drive, then their SHA-256 receipt into the checkout's `receipts/` tree. Drive first: a failed Drive write leaves no
receipt, so a reader never trusts a file that is not there. Committing the receipts is the caller's step (the A16f
committer), so a run can publish several files in one commit."""

from __future__ import annotations

import hashlib
import secrets
from collections.abc import Callable
from datetime import UTC, datetime

from ..models import now_utc
from .raw_store import RawFileStore, path_parts
from .receipts import Receipt, ReceiptFolder

RUN_ID_TIME = "%Y%m%dT%H%M%SZ"
RECEIPT_BREAKERS = ("\t", "\n", "\r")
WRITER, RUN_ID = "writer", "run_id"
BAD_FIELD = "{name} must be non-empty without tabs or line breaks: {value!r}"


def new_run_id(now: datetime | None = None) -> str:
    """Unique per run and sortable by time: `20261016T073000Z-1a2b3c` (UTC)."""
    stamp = (now or now_utc()).astimezone(UTC).strftime(RUN_ID_TIME)
    return f"{stamp}-{secrets.token_hex(3)}"


class DataStore:
    def __init__(self, drive: RawFileStore, area: str, receipts: ReceiptFolder, writer: str, run_id: str,
                 clock: Callable[[], datetime] = lambda: now_utc()):  # fmt: skip
        """`drive`: the whole project folder; `area`: the Drive area every path of this store lives under."""
        path_parts(area)
        for name, value in ((WRITER, writer), (RUN_ID, run_id)):  # a tab or line break would split a receipt line
            if not value or any(c in value for c in RECEIPT_BREAKERS):
                raise ValueError(BAD_FIELD.format(name=name, value=value))
        self.drive, self.area, self.receipts = drive, area, receipts
        self.writer, self.run_id, self.clock = writer, run_id, clock

    def put(self, path: str, data: bytes) -> Receipt:
        """Saves the file once (same bytes again: no-op; different bytes: RawFileConflict) and returns its receipt."""
        drive_path = f"{self.area}/{path}"
        self.drive.put(drive_path, data)
        receipt = Receipt(drive_path, hashlib.sha256(data).hexdigest(), len(data),
                          self.clock().astimezone(UTC).isoformat(), self.writer, self.run_id)  # fmt: skip
        return self.receipts.write(receipt)
