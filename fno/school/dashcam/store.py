"""`DashcamStore` over O9's `DataStore` (story 3.4): one gz JSONL file per (session, slot, kind), saved write-once to
Drive with its receipt, the receipt committed and pushed before `seal` returns. Equal records give equal bytes, so a
rerun is a no-op that returns the same seal; other bytes for the same key are a replay conflict. A file stored by a
run that stopped before its receipt's push is adopted by the writer's rerun (`recover`), never sealed over."""

import hashlib
from datetime import date

from ...storage.data_store import DataStore
from ...storage.raw_store import RawFileConflict
from ...storage.receipt_publisher import ReceiptPublisher
from ..constants import RecordKind
from ..contracts.dashcam import Belongs, ReplayConflict
from ..contracts.seal import Seal, StaleSeal
from ..contracts.slot_file import SlotRecord, decode_slot_file, encode_slot_file
from .adoption import adoptable
from .names import slot_file_path
from .reader import SlotFileReader

RULE_BROKEN = "rule broken: {path} is sealed with other bytes; a sealed file is never overwritten"
RECEIPT_MESSAGE = "dashcam {kind} {session} {slot}"
ADOPTED_MESSAGE = "dashcam {kind} {session} {slot} adopted: stored on Drive by a run stopped before its receipt"
DAMAGED = "{path} holds other bytes than its seal's SHA-256"


class DriveDashcamStore:
    def __init__(self, data: DataStore, publisher: ReceiptPublisher, reader: SlotFileReader):
        self.data, self.publisher, self.reader = data, publisher, reader

    def seal(self, session: date, slot: str, kind: RecordKind, records: tuple[SlotRecord, ...]) -> Seal:
        path, payload = slot_file_path(session, slot, kind), encode_slot_file(records)
        existing = self.find(session, slot, kind)
        if existing is not None:  # judged on the remote's receipt, before Drive is touched
            if existing.sha256 != hashlib.sha256(payload).hexdigest():
                raise ReplayConflict(RULE_BROKEN.format(path=path))
            return existing
        try:
            receipt = self.data.put(path, payload)
        except RawFileConflict as conflict:
            raise ReplayConflict(RULE_BROKEN.format(path=path)) from conflict
        pushed = self.publisher.publish(receipt.path, RECEIPT_MESSAGE.format(kind=kind, session=session, slot=slot))
        return Seal(path, receipt.sha256, pushed.pushed_at, pushed.commit)

    def recover(self, session: date, slot: str, kind: RecordKind, belongs: Belongs) -> Seal | None:
        found = self.find(session, slot, kind)
        if found is not None:
            return found
        path = slot_file_path(session, slot, kind)
        stored = self.data.drive.get(f"{self.data.area}/{path}")
        if stored is None:
            return None
        adoptable(stored, session, slot, kind, belongs)
        receipt = self.data.put(path, stored)  # the same bytes: a no-op on Drive, the receipt written from them
        pushed = self.publisher.publish(receipt.path, ADOPTED_MESSAGE.format(kind=kind, session=session, slot=slot))
        return Seal(path, receipt.sha256, pushed.pushed_at, pushed.commit)

    def read(self, seal: Seal) -> tuple[SlotRecord, ...]:
        data = self.reader.read(seal.path)
        if hashlib.sha256(data).hexdigest() != seal.sha256:
            raise StaleSeal(DAMAGED.format(path=seal.path))
        return decode_slot_file(data)

    def find(self, session: date, slot: str, kind: RecordKind) -> Seal | None:
        """The seal already made for this key, or None: a rerun can skip what is sealed."""
        path = slot_file_path(session, slot, kind)
        drive_path = f"{self.data.area}/{path}"
        pushed = self.publisher.published(drive_path)
        return Seal(path, pushed.sha256, pushed.pushed_at, pushed.commit) if pushed else None
