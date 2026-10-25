"""Write-once with a pushed receipt (stories REC1b and REC1c), the school dashcam's pattern in one place: a path already
receipted is never written again and its stored bytes are returned; bytes on Drive with no receipt (a save stopped
before its push) are adopted when they read as the path's own record, and the first bytes stand; nothing is ever
written over. A bug keeps its traceback; any other failure is `NotSaved`, named by type only (no secret)."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass

from ..storage.raw_store import RawFileConflict
from ..storage.receipt_publisher import ReceiptPublisher

CONFLICT = "{path}: Drive holds other bytes; nothing was written over them"
STUCK = "{path}: Drive holds bytes that are not its record ({why}); nothing was written over them"
MISSING = "receipted but missing on Drive"
PROGRAMMING_ERRORS = (TypeError, KeyError, AttributeError, NameError)


class NotSaved(Exception):
    """The record or its receipt could not be saved and pushed: nothing may be posted."""


class NotOurs(Exception):
    """Raised by a `vouch` callback: the stored bytes are not the record this path holds."""


@dataclass(frozen=True)
class Kept:
    path: str
    payload: bytes  # the bytes that stand at the path: an earlier record's when one was already there
    sha256: str
    receipt_commit: str
    already: bool  # receipted before this call
    adopted: bool  # found on Drive without a receipt and receipted now


class WriteOnce:
    def __init__(self, data, publisher: ReceiptPublisher):
        """`data`: O9's `DataStore` for the data area; `publisher`: commits and pushes the receipt to `main`."""
        self.data, self.publisher = data, publisher

    def keep(self, path: str, payload: bytes, vouch: Callable[[bytes], None], message: str) -> Kept:
        """`vouch(bytes)` raises `NotOurs` when stored bytes are not this path's record."""
        try:
            return self._keep(path, payload, vouch, message)
        except (NotSaved, *PROGRAMMING_ERRORS):
            raise
        except RawFileConflict:
            raise NotSaved(CONFLICT.format(path=path)) from None
        except Exception as failed:  # a refused push, a Drive error: never posted, named by type only
            raise NotSaved(f"{path}: {type(failed).__name__}") from None

    def _keep(self, path: str, payload: bytes, vouch: Callable[[bytes], None], message: str) -> Kept:
        drive_path = f"{self.data.area}/{path}"
        existing = self.publisher.published(drive_path)  # judged on the remote's receipt, before Drive is touched
        held = self.data.drive.get(drive_path)
        if existing is not None:
            stands = _vouched(held, vouch, path)
            return Kept(path, stands, existing.sha256, existing.commit, already=True, adopted=False)
        stands = payload if held is None else _vouched(held, vouch, path)
        receipt = self.data.put(path, stands)  # the same bytes as Drive holds: a no-op, the receipt written
        pushed = self.publisher.publish(receipt.path, message)
        return Kept(path, stands, hashlib.sha256(stands).hexdigest(), pushed.commit, already=False,
                    adopted=held is not None)  # fmt: skip


def _vouched(held: bytes | None, vouch: Callable[[bytes], None], path: str) -> bytes:
    if held is None:
        raise NotSaved(STUCK.format(path=path, why=MISSING))
    try:
        vouch(held)
    except NotOurs as refused:
        raise NotSaved(STUCK.format(path=path, why=refused)) from None
    return held
