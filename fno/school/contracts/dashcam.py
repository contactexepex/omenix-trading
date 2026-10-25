"""The dashcam port (story 3.4): write-once files of records, the decisions file sealed before any fill."""

from collections.abc import Callable
from datetime import date
from typing import Protocol, runtime_checkable

from ..constants import RecordKind
from .seal import Seal
from .slot_file import SlotRecord


class ReplayConflict(Exception):
    """Other bytes for a (session, slot, kind) already sealed: never overwritten, reported as "rule broken"."""


class DashcamStuck(Exception):
    """A file stored for a key with no receipt on `main` that cannot be adopted as this run's record: the run stops
    by name ("dashcam stuck: stored file unverifiable ..."), never recomputing over it."""


Belongs = Callable[[SlotRecord], bool]  # the writer's own test that a record is its own (its drivers, its cards)


@runtime_checkable
class DashcamStore(Protocol):
    def seal(self, session: date, slot: str, kind: RecordKind, records: tuple[SlotRecord, ...]) -> Seal:
        """Encode with `encode_slot_file`, save once and push its receipt; the same records again return the same seal,
        other records for the same key raise `ReplayConflict`."""

    def find(self, session: date, slot: str, kind: RecordKind) -> Seal | None:
        """The seal of that file if it was sealed (a rerun skips it; reports and the replay comparator read it)."""

    def recover(self, session: date, slot: str, kind: RecordKind, belongs: Belongs) -> Seal | None:
        """For the writer's rerun (MS-P1c follow-up): `find`, else a file stored for the key whose receipt never
        reached `main` (a run stopped between the two) is adopted: checked to be the key's and the writer's own
        (`belongs`, every record), its receipt published from its own bytes, its seal returned. A rerun computes
        what it no longer could reproduce (a driver's deadline, a capture landed since), so it never seals over it.
        A stored file that fails the check raises `DashcamStuck`."""

    def read(self, seal: Seal) -> tuple[SlotRecord, ...]:
        """The sealed records, their bytes checked against the seal's SHA-256 (`StaleSeal` if they differ)."""
