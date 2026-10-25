"""The path reader (story MS-INS, part a): every trade and ticket closed on a range of sessions, joined to the sealed
decision it rests on, its exit record and the road's verified snapshot on each trading session it was held. Reads only;
whatever cannot be verified becomes a `DataFault` on the path, never a guess, and a damaged file never stops the read.

Corrections (orchestrator's ruling on judge 501): a dashcam file is written once, so a correction is sealed on a later
session than its original. There is one resolver: an original closed on day d is read on day d as its latest
correction, wherever and whenever that correction was sealed up to today, or up to the session `as_of` names (a
session's instructor run reads only files sealed by then, so a rerun reads the same; judge 525). A correction is never
a path on the day its own file was sealed. So the paths of `closed_on` over each day of a range are exactly
`closed_between` over the range. A day's tally recomputed after a correction can change; the 20:05 line keeps what was
known at 20:05."""

from dataclasses import dataclass
from datetime import date

from ...models import IST
from ...research_data.calendar import SessionCalendar
from ...storage.trading_days import is_trading_day
from ..constants import SLOT_1500, ExitReason, Outcome, RecordKind
from ..contracts.accounts import IndexSettlementSource, SettlementUnavailable
from ..contracts.clock import Clock
from ..contracts.dashcam import DashcamStore
from ..contracts.records import DecisionRecord, ExitRecord, OutcomeRecord
from ..contracts.roads import ROADS_BY_CODE
from ..contracts.seal import StaleSeal
from ..contracts.slot_file import SlotRecord
from ..contracts.snapshot import SlotSnapshot
from .contracts import ClosedRead, DataFault, HeldPath, net_matches_fills, record_sha256
from .ports import SnapshotArchive

RECORD_START = date(2026, 10, 22)  # the school's code exists from this day: no dashcam file can be older


def latest(record: OutcomeRecord, corrections: dict[str, OutcomeRecord]) -> OutcomeRecord:
    """The record as its corrections leave it: each correction replaced by the one that corrects it, in turn."""
    seen = set()
    while (sha := record_sha256(record)) in corrections and sha not in seen:
        seen.add(sha)
        record = corrections[sha]
    return record


@dataclass(frozen=True)
class SealedFile:
    records: tuple[SlotRecord, ...]
    sha256: str
    damaged: bool  # its bytes differ from its seal: no record of it is used


class PathReader:
    def __init__(self, dashcam: DashcamStore, snapshots: SnapshotArchive, settlements: IndexSettlementSource,
                 calendar: SessionCalendar, clock: Clock, record_start: date = RECORD_START):  # fmt: skip
        self.dashcam, self.snapshots, self.settlements = dashcam, snapshots, settlements
        self.calendar, self.clock, self.record_start = calendar, clock, record_start
        self._files: dict[tuple[date, RecordKind], SealedFile | None] = {}  # one read per file per run

    def closed_on(self, session: date, as_of: date | None = None) -> ClosedRead:
        return self.closed_between(session, session, as_of)

    def closed_between(self, first: date, last: date, as_of: date | None = None) -> ClosedRead:
        """Every original closed from `first` to `last`, each as its latest correction sealed up to `as_of` (None:
        today), never before `last`."""
        upto = max(as_of or self.clock.now().astimezone(IST).date(), last)
        files = {d: self._read(d, RecordKind.OUTCOMES) for d in self.sessions(first, upto)}
        outcomes = {d: [r for r in f.records if isinstance(r, OutcomeRecord)] for d, f in files.items() if f}
        corrections = {r.corrects: r for d in sorted(outcomes) for r in outcomes[d] if r.corrects}
        paths = tuple(self._path(latest(r, corrections)) for d in sorted(outcomes) if d <= last
                      for r in outcomes[d] if not r.corrects)  # fmt: skip
        return ClosedRead(paths, tuple(d for d, f in files.items() if f and f.damaged))

    def orphan_corrections(self) -> tuple[OutcomeRecord, ...]:
        """Corrections whose `corrects` names no outcome on file at all, from the start of the record to today: counted
        and alerted by every report and day's run, never dropped silently (judges 501.1 and 522)."""
        today = self.clock.now().astimezone(IST).date()
        files = (self._read(d, RecordKind.OUTCOMES) for d in self.sessions(self.record_start, today))
        outcomes = [r for f in files if f for r in f.records if isinstance(r, OutcomeRecord)]
        known = {record_sha256(r) for r in outcomes}
        return tuple(r for r in outcomes if r.corrects and r.corrects not in known)

    def sessions(self, first: date, last: date) -> list[date]:
        """The trading sessions from `first` to `last`, by A7's calendar."""
        return [d for d in self.calendar.sessions(first, last) if is_trading_day(self.calendar, d)]

    def _read(self, session: date, kind: RecordKind) -> SealedFile | None:
        if (session, kind) not in self._files:
            self._files[(session, kind)] = self._read_sealed(session, kind)
        return self._files[(session, kind)]

    def _read_sealed(self, session: date, kind: RecordKind) -> SealedFile | None:
        seal = self.dashcam.find(session, SLOT_1500, kind)
        if seal is None:
            return None
        try:
            return SealedFile(self.dashcam.read(seal), seal.sha256, False)
        except StaleSeal:
            return SealedFile((), seal.sha256, True)

    def _path(self, outcome: OutcomeRecord) -> HeldPath:
        entry_day, exit_day = _ist_day(outcome.entry.filled_at), _ist_day(outcome.exit.filled_at)
        faults: list[DataFault] = []
        entry = self._entry(outcome, entry_day, faults)
        snapshots, skipped, exit_record = [], 0, None
        for day in self.sessions(entry_day, exit_day):
            sealed = self._read(day, RecordKind.DECISIONS)
            if sealed is None or sealed.damaged:
                faults.append(DataFault.SESSION_NOT_SEALED if sealed is None else DataFault.SEALED_FILE_DAMAGED)
                continue
            snapshot, closed = self._snapshot(outcome, day, sealed.records, faults)
            skipped += closed
            snapshots += [snapshot] if snapshot else []
            exit_record = exit_record or _exit_record(outcome, sealed.records)
        settled = outcome.exit_reason == ExitReason.EXPIRY
        if not snapshots or snapshots[0].session != entry_day or (not settled and snapshots[-1].session != exit_day):
            faults.append(DataFault.SNAPSHOT_MISSING)
        if not settled:
            _check_exit(outcome, exit_record, faults)
        if not net_matches_fills(outcome):
            faults.append(DataFault.NET_MISMATCH_FILLS)
        settlement = self._settlement(outcome, exit_day, faults) if settled else None
        unique = tuple(dict.fromkeys(faults))
        return HeldPath(outcome, entry, exit_record, tuple(snapshots), settlement, skipped, unique)

    def _entry(self, outcome: OutcomeRecord, day: date, faults: list[DataFault]) -> DecisionRecord | None:
        sealed = self._read(day, RecordKind.DECISIONS)
        if sealed is not None and sealed.damaged:
            faults.append(DataFault.SEALED_FILE_DAMAGED)
            return None
        wanted = Outcome.TICKET if outcome.is_ticket else Outcome.TRADE
        mine = (
            r for r in (sealed.records if sealed else ()) if isinstance(r, DecisionRecord) and r.road == outcome.road
        )
        entry = next(
            (r for r in mine if (r.decision.driver_id, r.decision.outcome) == (outcome.driver_id, wanted)), None
        )
        if entry is None:
            faults.append(DataFault.ENTRY_DECISION_MISSING)
        elif sealed.sha256 != outcome.decision_sha256:
            faults.append(DataFault.ENTRY_SEAL_MISMATCH)
        return entry

    def _snapshot(self, outcome, day, records, faults) -> tuple[SlotSnapshot | None, bool]:
        """The session's verified snapshot, or None; True when a sealed closure of the road explains its absence."""
        on_road = [r for r in records if isinstance(r, DecisionRecord) and r.road == outcome.road]
        named = next((r for r in on_road if r.snapshot_sha256), None)
        if named is None:
            closed = any(r.road_closed_by is not None for r in on_road)
            if not closed:
                faults.append(DataFault.SNAPSHOT_MISSING)
            return None, closed  # a closed road: its step merges with the next
        snapshot = self.snapshots.snapshot(outcome.road, day)
        if snapshot is None:
            faults.append(DataFault.SNAPSHOT_MISSING)
        elif (snapshot.sha256, snapshot.snapshot_id) != (named.snapshot_sha256, named.snapshot_id):
            faults.append(DataFault.SNAPSHOT_HASH_MISMATCH)
        else:
            return snapshot, False
        return None, False

    def _settlement(self, outcome: OutcomeRecord, expiry: date, faults: list[DataFault]) -> float | None:
        try:
            final = self.settlements.price(ROADS_BY_CODE[outcome.road].underlying, expiry)
        except SettlementUnavailable:
            faults.append(DataFault.SETTLEMENT_MISSING)
            return None
        if final.file_sha256 != outcome.exit.rests_on:
            faults.append(DataFault.SETTLEMENT_MISMATCH)
            return None
        return final.price


def _ist_day(at) -> date:
    return at.astimezone(IST).date()


def _exit_record(outcome: OutcomeRecord, records: tuple[SlotRecord, ...]) -> ExitRecord | None:
    return next((r for r in records if isinstance(r, ExitRecord) and r.position_id == outcome.position_id), None)


def _check_exit(outcome: OutcomeRecord, record: ExitRecord | None, faults: list[DataFault]) -> None:
    """An exit rule's close leaves an exit record (story 3.4): causes 6 and 11 read it."""
    if record is None:
        faults.append(DataFault.EXIT_RECORD_MISSING)
    elif (record.driver_id, record.road, record.exit_reason) != (outcome.driver_id, outcome.road, outcome.exit_reason):
        faults.append(DataFault.EXIT_RECORD_MISMATCH)
