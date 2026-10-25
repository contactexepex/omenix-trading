"""The 3 pm quote store under the owner's rule of 15 Oct 2026 ("6 A", story A4b): raw Groww quote rows go to Google
Drive only; the public repository keeps each attempt's sidecar (times, counts, the Drive file's SHA-256 and the
derived levels) and the day's canonical marker.

A Groww quote file is read back only when its bytes hash to the `csv_sha256` of the sidecar committed with it, so a
Drive copy changed later is refused, never used. A saved file that cannot be read is an error, never a quiet "absent":
a reader that took "absent" for "no snapshot" would lose a day without saying so.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable

from ..storage.raw_store import RawFileStore
from .recorder import RAW_FILE_SAVED

QUOTE_FILE, SIDECAR = ".csv", ".meta.json"


class RawQuoteStoreUnavailable(RuntimeError):
    """No private store is set up (the Drive settings are missing): a raw quote file can be neither saved nor read."""


class RawQuoteMissing(RuntimeError):
    """The sidecar says the quote file was saved, but the private store does not have it."""


class RawQuoteHashMismatch(RuntimeError):
    """The private store's copy does not hash to the committed sidecar's `csv_sha256`."""


class DriveOnlyQuoteStore(RawFileStore):
    def __init__(self, repository: RawFileStore, private: Callable[[], RawFileStore | None], private_dataset: str,
                 unavailable: str):  # fmt: skip
        """`private` is called on first use, so building this store never signs in to Drive; `unavailable` says
        which settings are missing when it returns None (names only, never values)."""
        self.repository, self._private_factory, self._private = repository, private, None
        self.prefix, self.unavailable = f"{private_dataset}/", unavailable
        self.name = f"{repository.name} + private quote files"

    def is_raw(self, path: str) -> bool:
        return path.startswith(self.prefix) and path.endswith(QUOTE_FILE)

    def put(self, path: str, data: bytes) -> None:
        (self._private_store() if self.is_raw(path) else self.repository).put(path, data)

    def get(self, path: str) -> bytes | None:
        if not self.is_raw(path):
            return self.repository.get(path)
        sidecar = self.repository.get(path.removesuffix(QUOTE_FILE) + SIDECAR)
        if sidecar is None:
            return None
        meta = json.loads(sidecar)
        if not meta.get(RAW_FILE_SAVED, True):
            return None
        data = self._private_store().get(path)
        if data is None:
            raise RawQuoteMissing(f"{path}: its sidecar says it was saved, but the private store does not have it")
        if hashlib.sha256(data).hexdigest() != meta.get("csv_sha256"):
            raise RawQuoteHashMismatch(f"{path}: the private copy does not match the committed sidecar's csv_sha256")
        return data

    def _private_store(self) -> RawFileStore:
        if self._private is None:
            self._private = self._private_factory()
        if self._private is None:
            raise RawQuoteStoreUnavailable(f"raw quote files live in Google Drive only: set {self.unavailable}")
        return self._private
