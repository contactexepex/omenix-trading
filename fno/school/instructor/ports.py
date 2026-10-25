"""The instructor's ports (story MS-INS, part a). Each reads a recorded input, never a live one; the store is the only
writer and writes only the instructor's own files. The settlement price is read through d's `IndexSettlementSource`
and the sealed records through c's `DashcamStore`, unchanged: no second port for either."""

from datetime import date
from enum import StrEnum
from typing import Protocol, runtime_checkable

from ..constants import RoadCode
from ..contracts.decisions import Decision
from ..contracts.records import DecisionRecord
from ..contracts.snapshot import SlotSnapshot
from .contracts import Attribution, Classification, PairedRow

InstructorRecord = Attribution | Classification | PairedRow


class InstructorKind(StrEnum):
    ATTRIBUTION = "attribution"
    CAUSES = "causes"
    PAIRED = "paired"


class InstructorConflict(Exception):
    """Other bytes for an instructor file already written: never overwritten."""


@runtime_checkable
class SnapshotArchive(Protocol):
    def snapshot(self, road: RoadCode, session: date) -> SlotSnapshot | None:
        """The road's recorded capture of that session, verified against its sidecar; None when the road had none."""


@runtime_checkable
class EventCalendar(Protocol):
    def known_between(self, decided_on: date, after: date, through: date) -> tuple[date, ...]:
        """The days of A6's scheduled events known on `decided_on` and dated after `after`, on or before `through`."""


@runtime_checkable
class CardReplay(Protocol):
    def replay(self, record: DecisionRecord) -> Decision | None:
        """The frozen card's decision on the record's own snapshot and history; None when it cannot be replayed."""


@runtime_checkable
class StopSource(Protocol):
    def loss_multiple(self, driver_id: str) -> float | None:
        """The frozen card's stop as a multiple of the entry credit or debit; None when the card has no stop."""


@runtime_checkable
class InstructorStore(Protocol):
    def write(self, session: date, kind: InstructorKind, records: tuple[InstructorRecord, ...]) -> str:
        """Write once and return the file's SHA-256; the same records again return it, others raise
        `InstructorConflict`."""

    def read(self, session: date, kind: InstructorKind) -> tuple[InstructorRecord, ...] | None:
        """The records written for that key, or None."""
