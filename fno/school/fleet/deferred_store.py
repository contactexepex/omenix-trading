"""The instructor's store as its session step's work sees it (story MS-P1j, judge 523): reads go to the real store, and
writes are only kept, in order, until `flush` writes them on the run's own thread. So the work, which runs on a thread
under a time limit, never writes to Drive or the checkout: a work past its limit leaves nothing behind."""

import hashlib
from datetime import date

from ..instructor.ports import InstructorKind, InstructorRecord, InstructorStore
from ..instructor.records_file import encode_instructor_file


class DeferredInstructorStore:
    def __init__(self, store: InstructorStore):
        self.store = store
        self.pending: dict[tuple[date, InstructorKind], tuple[InstructorRecord, ...]] = {}

    def write(self, session: date, kind: InstructorKind, records: tuple[InstructorRecord, ...]) -> str:
        self.pending[(session, kind)] = records
        return hashlib.sha256(encode_instructor_file(records)).hexdigest()

    def read(self, session: date, kind: InstructorKind) -> tuple[InstructorRecord, ...] | None:
        kept = self.pending.get((session, kind))
        return kept if kept is not None else self.store.read(session, kind)

    def flush(self) -> None:
        """The kept writes, in the order made: the real store's write-once rules apply to each."""
        for (session, kind), records in self.pending.items():
            self.store.write(session, kind, records)
