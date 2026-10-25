"""The dashcam of a replay (story MS-P1j; `RunMode.REPLAY`: a recorded session again, fixed clock, local store, nothing
pushed): write-once slot files in a local folder, with seals that say they were never pushed (`commit` "replay").
Never the paper record: a replay's seals prove nothing about a fill's order, and nothing reads them as evidence.

`encode` and `decode` are the one place a subclass changes (the simulator's practice dashcam labels each line); the
write-once and seal logic stays here."""

import hashlib
from datetime import date
from pathlib import Path

from ..constants import RecordKind
from ..contracts.clock import Clock
from ..contracts.dashcam import Belongs, ReplayConflict
from ..contracts.seal import Seal, StaleSeal
from ..contracts.slot_file import SlotRecord, decode_slot_file, encode_slot_file
from ..dashcam.names import slot_file_path

REPLAY_COMMIT = "replay"


class ReplayDashcam:
    def __init__(self, folder: Path, clock: Clock):
        self.folder, self.clock = Path(folder), clock

    def seal(self, session: date, slot: str, kind: RecordKind, records: tuple[SlotRecord, ...]) -> Seal:
        path, payload = slot_file_path(session, slot, kind), self.encode(records)
        file = self.folder / path
        if file.is_file() and file.read_bytes() != payload:
            raise ReplayConflict(path)
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(payload)
        return self._seal(path, payload)

    def find(self, session: date, slot: str, kind: RecordKind) -> Seal | None:
        path = slot_file_path(session, slot, kind)
        file = self.folder / path
        return self._seal(path, file.read_bytes()) if file.is_file() else None

    def recover(self, session: date, slot: str, kind: RecordKind, belongs: Belongs) -> Seal | None:
        """A local file is its own seal: nothing is pushed, so no run stops between a write and a receipt."""
        return self.find(session, slot, kind)

    def read(self, seal: Seal) -> tuple[SlotRecord, ...]:
        file = self.folder / seal.path
        data = file.read_bytes() if file.is_file() else b""
        if hashlib.sha256(data).hexdigest() != seal.sha256:
            raise StaleSeal(seal.path)
        return self.decode(data)

    def encode(self, records: tuple[SlotRecord, ...]) -> bytes:
        return encode_slot_file(records)

    def decode(self, data: bytes) -> tuple[SlotRecord, ...]:
        return decode_slot_file(data)

    def _seal(self, path: str, payload: bytes) -> Seal:
        return Seal(path, hashlib.sha256(payload).hexdigest(), self.clock.now(), REPLAY_COMMIT)
