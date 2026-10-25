"""The replay reader (story 3.4, criterion 4): the records sealed for a (session, slot, kind), read back from Drive
through the receipts and nothing else, so a replay sees exactly what was sealed."""

from datetime import date

from ..constants import RecordKind
from ..contracts.seal import StaleSeal
from ..contracts.slot_file import SlotRecord
from .store import DriveDashcamStore

NOTHING_SEALED = "nothing is sealed for {kind} {session} {slot}"


class ReplayReader:
    def __init__(self, store: DriveDashcamStore):
        self.store = store

    def records(self, session: date, slot: str, kind: RecordKind) -> tuple[SlotRecord, ...]:
        seal = self.store.find(session, slot, kind)
        if seal is None:
            raise StaleSeal(NOTHING_SEALED.format(kind=kind, session=session, slot=slot))
        return self.store.read(seal)
