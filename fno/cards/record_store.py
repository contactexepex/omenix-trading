"""Where card records go (owner decision of 15 Oct 2026: Google Drive only, never the public repository).
`CardRecordStore` is the interface; `DriveCardRecords` writes into Drive's `cards` area under the archive rules (written
once: the same bytes again change nothing, different bytes at a path are refused). A failure is returned as a line,
by error type only, so no message from the store (which could carry a sign-in detail) reaches a log."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from ..storage.raw_store import RawFileStore

SAVED = "card record saved to Drive: {path}"
NOT_SAVED = "card record NOT saved to Drive: {reason}"
NO_DRIVE = "the owner's Drive settings (FNO_GDRIVE_*) are not set"


class CardRecordStore(ABC):
    @abstractmethod
    def save(self, day: date, name: str, data: bytes) -> tuple[bool, str]:
        """(saved, the line to print); never raises."""


class DriveCardRecords(CardRecordStore):
    def __init__(self, store: RawFileStore):
        self.store = store  # the `cards` area of the owner's Drive project folder

    def save(self, day: date, name: str, data: bytes) -> tuple[bool, str]:
        path = f"{day:%Y}/{day:%m}/{name}.json"
        try:
            self.store.put(path, data)
        except Exception as error:  # noqa: BLE001 - Drive down or refused: the card is already out; say so
            return False, NOT_SAVED.format(reason=type(error).__name__)
        return True, SAVED.format(path=path)


class NoCardRecords(CardRecordStore):
    def __init__(self, reason: str = NO_DRIVE):
        self.reason = reason

    def save(self, day: date, name: str, data: bytes) -> tuple[bool, str]:
        return False, NOT_SAVED.format(reason=self.reason)
