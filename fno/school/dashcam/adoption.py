"""Adopting a stored slot file whose receipt never reached `main` (story MS-P1c follow-up, orchestrator's go, 23 Oct
2026): a run stopped between the Drive write and the receipt's push, and a rerun cannot reproduce its records (a driver
past its time limit, a capture or margin file landed since), so sealing again would be refused for good. The stored
file is adopted only when it is the key's file and the writer's own; anything else stops the run by name."""

from datetime import date

from ..constants import RecordKind
from ..contracts.dashcam import Belongs, DashcamStuck
from ..contracts.records import DecisionRecord, DriftRow, ExitRecord, OutcomeRecord
from ..contracts.slot_file import SlotRecord, decode_slot_file, encode_slot_file

STUCK = "dashcam stuck: stored file unverifiable {session} {slot} {kind} ({why})"
KIND_TYPES = {RecordKind.DECISIONS: (DecisionRecord, ExitRecord), RecordKind.OUTCOMES: (OutcomeRecord,),
              RecordKind.DRIFT: (DriftRow,)}  # fmt: skip


def adoptable(stored: bytes, session: date, slot: str, kind: RecordKind, belongs: Belongs) -> tuple[SlotRecord, ...]:
    """The stored file's records when it decodes, re-encodes to the same bytes, holds only the kind's records of this
    session and slot, and every record is the writer's own; else `DashcamStuck`, naming why (never a value)."""

    def stuck(why: str) -> DashcamStuck:
        return DashcamStuck(STUCK.format(session=session, slot=slot, kind=kind, why=why))

    try:
        records = decode_slot_file(stored)
    except Exception as broken:  # noqa: BLE001 - any decoding failure means the bytes are not a slot file
        raise stuck(f"unreadable: {type(broken).__name__}") from broken
    if encode_slot_file(records) != stored:
        raise stuck("not canonical")
    if any(not isinstance(r, KIND_TYPES[kind]) for r in records):
        raise stuck(f"a record that is not {kind}")
    if any(_session(r, session) != session or getattr(r, "slot", slot) != slot for r in records):
        raise stuck("a record of another session or slot")
    if not all(belongs(r) for r in records):
        raise stuck("a record that is not this fleet's (another driver or card version)")
    return records


def _session(record: SlotRecord, session: date) -> date:
    """An outcome names no session: an expiry settled at a later session's start fills on its expiry day, so its
    file's session cannot be read from it; it is checked by its kind and as the writer's own only."""
    return session if isinstance(record, OutcomeRecord) else record.session
