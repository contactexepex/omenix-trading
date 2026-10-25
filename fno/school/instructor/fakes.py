"""In-memory fakes of the instructor's ports (story MS-INS, part a), for its tests. Each passes
`tests/school/instructor/conformance.py`, as every real adapter must. No production path imports this module."""

import hashlib
from dataclasses import dataclass, field
from datetime import date

from ..constants import RoadCode
from ..contracts.decisions import Decision
from ..contracts.records import DecisionRecord
from ..contracts.snapshot import SlotSnapshot
from .ports import InstructorConflict, InstructorKind, InstructorRecord
from .records_file import decode_instructor_file, encode_instructor_file


@dataclass
class FakeSnapshotArchive:
    snapshots: dict[tuple[RoadCode, date], SlotSnapshot] = field(default_factory=dict)

    def snapshot(self, road: RoadCode, session: date) -> SlotSnapshot | None:
        return self.snapshots.get((road, session))


@dataclass
class FakeEventCalendar:
    events: dict[date, date] = field(default_factory=dict)  # event day -> the day its date became known

    def known_between(self, decided_on: date, after: date, through: date) -> tuple[date, ...]:
        return tuple(
            sorted(day for day, known in self.events.items() if known <= decided_on and after < day <= through)
        )


@dataclass
class FakeCardReplay:
    replays: dict[str, Decision | None] = field(default_factory=dict)  # driver ID -> its replayed decision

    def replay(self, record: DecisionRecord) -> Decision | None:
        return self.replays.get(record.decision.driver_id, record.decision)


@dataclass
class FakeStopSource:
    multiples: dict[str, float] = field(default_factory=dict)  # driver ID -> its card's loss multiple

    def loss_multiple(self, driver_id: str) -> float | None:
        return self.multiples.get(driver_id)


@dataclass
class FakeInstructorStore:
    files: dict[tuple[date, InstructorKind], bytes] = field(default_factory=dict)

    def write(self, session: date, kind: InstructorKind, records: tuple[InstructorRecord, ...]) -> str:
        payload = encode_instructor_file(records)
        if self.files.get((session, kind), payload) != payload:
            raise InstructorConflict(f"{session} {kind}")
        self.files[(session, kind)] = payload
        return hashlib.sha256(payload).hexdigest()

    def read(self, session: date, kind: InstructorKind) -> tuple[InstructorRecord, ...] | None:
        payload = self.files.get((session, kind))
        return None if payload is None else decode_instructor_file(payload)
