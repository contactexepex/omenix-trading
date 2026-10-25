"""Where recommendations go (story REC1b, section 5): Drive, written once with the receipt pushed before anything is
posted, through `WriteOnce` (the dashcam's pattern). A day already receipted is never written again; its own stored
record is what a later run re-sends. A record on Drive with no receipt is adopted when it reads strictly as that day's
recommendation, and the first-made record stands."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .codec import decode, encode
from .contracts import Recommendation, RecordRefused
from .write_once import NotOurs, NotSaved, WriteOnce

AREA_FOLDER = "recommend"
RECEIPT_MESSAGE = "Receipt: the recommendation of {day}"
OTHER_DAY = "a record of {day}"

__all__ = ["AREA_FOLDER", "DriveRecommendations", "NotSaved", "Saved", "Stored", "record_path"]


@dataclass(frozen=True)
class Saved:
    path: str  # the record's Drive path inside the data area
    sha256: str
    receipt_commit: str


@dataclass(frozen=True)
class Stored:
    record: Recommendation  # the day's record as it stands: an adopted earlier one wins over a new one
    saved: Saved
    already: bool  # receipted before this run: its line is re-sent, labelled, never lost silently
    adopted: bool  # found on Drive without a receipt and receipted now


def record_path(day: date) -> str:
    return f"{AREA_FOLDER}/{day:%Y}/{day:%m}/{day.isoformat()}.json"


class DriveRecommendations:
    def __init__(self, data, publisher):
        self.keeper = WriteOnce(data, publisher)

    def save(self, record: Recommendation) -> Stored:
        kept = self.keeper.keep(record_path(record.session), encode(record), _vouch_for(record.session),
                                RECEIPT_MESSAGE.format(day=record.session))  # fmt: skip
        return Stored(decode(kept.payload), Saved(kept.path, kept.sha256, kept.receipt_commit), kept.already,
                      kept.adopted)  # fmt: skip


def _vouch_for(day: date):
    def vouch(held: bytes) -> None:
        try:
            stored = decode(held)
        except RecordRefused as refused:
            raise NotOurs(str(refused)) from None
        if stored.session != day:
            raise NotOurs(OTHER_DAY.format(day=stored.session))

    return vouch
