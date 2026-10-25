"""The fleet runner (story MS-P1j): one session of every driver on every road, in the story's order. It has no switch:
`school.enabled` is the pilot's, read by its entry points (the record root and `school run`), so the simulator's
practice command runs the same fleet without one (orchestrator, 23 Oct 2026).

1. Expired positions settle before the session's first account view (judge 486's note).
2. If the session's decisions file is already sealed, nothing is decided or sealed again; the finish below runs
   once more, so a crash anywhere between the seal and the counts' commit is completed, never doubled.
3. Otherwise: the roads and the quality gate (`plan_slot`); each driver isolated (`DriverStep`); one decisions file
   sealed with every decision and exit record before any fill; then the fills (`FillStep`).
4. The finish (`_finish`), rebuilt from the sealed records and the ledgers on every run: the fills not yet recorded
   (`FillStep`), the outcomes and drift files each sealed once, the step after the outcomes (the instructor's
   session run, isolated by its root), and the counts written and committed by this one runner. A session whose
   outcomes, drift and counts all exist runs that step again and commits what is still uncommitted."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol

from ...desk.settlement import SETTLEMENT_TIME as SESSION_CLOSE
from ...desk.snapshot import ExecutionSnapshot
from ...models import IST
from ..constants import FLEET_STOPPED, SLOT_1500, SLOT_LAST_START, ExitReason, RecordKind, RoadCode
from ..contracts.clock import Clock
from ..contracts.dashcam import DashcamStore, DashcamStuck
from ..contracts.decisions import Driver, SpotPoint
from ..contracts.fleet import RunMode, SessionRun
from ..contracts.records import DecisionRecord, DriftRow, ExitRecord
from ..contracts.roads import ROADS_BY_CODE, Road, RoadCatalogue
from ..contracts.snapshot import SlotSnapshot, SnapshotSource
from ..execution.quote_rules import LIVE, QuoteRules
from ..settings import SchoolSettings
from ..tickets.counts import counts_for
from .books import AccountUnreadable, Books, EntryMids, account_call
from .card_check import no_check
from .counts_file import SessionCounts
from .decide import DriverStep
from .fill import FillStep, SlotFills
from .ledgers import open_positions, recorded
from .outcomes import outcomes_of
from .running_view import driver_of
from .session_hook import no_step
from .settle import settle_expired
from .slot import QualityGate, SlotRoads, plan_slot

FINISHED = (RecordKind.OUTCOMES, RecordKind.DRIFT)
LATE_RERUN = "rerun after 15:30, fillable may differ"  # ruling b's accepted limit, marked on the session's record
ACCOUNT_STOP = FLEET_STOPPED + " account unreadable {reason}"  # the run's status; the CLI exits 1: an alert
DASHCAM_STOP = FLEET_STOPPED + " {reason}"  # "dashcam stuck: stored file unverifiable ...": the CLI exits 1
FIRST_SEAL_TOO_LATE = (FLEET_STOPPED + " too late for a first seal: {now:%H:%M:%S} IST is after the slot's last start, "
                       "{by:%H:%M} IST on {session}; nothing sealed")  # MS-P1j3; the CLI exits 1  # fmt: skip
CardCheck = Callable[[tuple[DecisionRecord, ...], object], tuple[str, ...]]  # (sealed decisions, their seal)
LawsFor = Callable[[Mapping[RoadCode, SlotSnapshot]], object]  # the slot's `SafetyLaws`, built on its marks


class SpotHistory(Protocol):
    def spots(self, road: Road, session: date) -> tuple[SpotPoint, ...]: ...


@dataclass
class SchoolFleet:
    settings: SchoolSettings
    catalogue: RoadCatalogue
    snapshots: SnapshotSource
    gate: QualityGate
    history: SpotHistory
    drivers: tuple[Driver, ...]
    laws_for: LawsFor
    books: Books
    dashcam: DashcamStore
    counts: SessionCounts
    capture_1515: Callable[[date], ExecutionSnapshot | None]
    entry_mids: EntryMids
    clock: Clock
    seconds_per_driver: float = 60.0
    card_check: CardCheck = no_check  # the record's comparison-card mismatch check; a replay has none
    rules: QuoteRules = LIVE  # d's quote rules: only the simulator's practice root passes practice rules
    after_outcomes: Callable[[date], None] = no_step  # e.g. the instructor's session run (isolated by its root)

    def run(self, session: date, mode: RunMode) -> SessionRun:
        try:
            return self._run(session, mode)
        except AccountUnreadable as stop:
            return SessionRun(session, mode, ACCOUNT_STOP.format(reason=stop))
        except DashcamStuck as stuck:
            return SessionRun(session, mode, DASHCAM_STOP.format(reason=stuck))

    def _run(self, session: date, mode: RunMode) -> SessionRun:
        started = self.clock.now()  # before the captures are read: the run's start decides, never its reading time
        roads = plan_slot(session, self.catalogue, self.snapshots, self.gate, self.rules)
        if not roads.scheduled:
            return SessionRun(session, mode, "")
        found = self.dashcam.recover(session, SLOT_1500, RecordKind.DECISIONS, self._belongs)
        if found is not None:
            records, exits = self._sealed(found)
            _, refused = self._finish(roads, records, exits, found, rerun=True)
            return SessionRun(session, mode, "", records, found, warnings=(*self.card_check(records, found), *refused))
        late = self._too_late_to_seal(session, mode, started)
        if late:
            return SessionRun(session, mode, late)
        settled = settle_expired(self.books, self._ids(), session)
        records, exits = self._decide(roads, session)
        seal = self.dashcam.seal(session, SLOT_1500, RecordKind.DECISIONS, (*records, *settled, *exits))
        fills, refused = self._finish(roads, records, (*settled, *exits), seal)
        return SessionRun(session, mode, "", records, seal, fills.fills, (*self.card_check(records, seal), *refused))

    @staticmethod
    def _too_late_to_seal(session: date, mode: RunMode, started: datetime) -> str:
        """MS-P1j3: a RECORD run started after the slot's last start makes no first seal (law 6 would refuse every
        fill, spending the session's one record); a replay, which records nothing, never stops here."""
        last = datetime.combine(session, SLOT_LAST_START, IST)
        if mode is not RunMode.RECORD or started <= last:
            return ""
        return FIRST_SEAL_TOO_LATE.format(now=started.astimezone(IST), by=SLOT_LAST_START, session=session)

    def _decide(self, roads: SlotRoads, session: date) -> tuple[tuple[DecisionRecord, ...], tuple[ExitRecord, ...]]:
        laws = self.laws_for(roads.marks)
        step = DriverStep(laws.check, lambda code: self.history.spots(ROADS_BY_CODE[code], session),
                          self.settings.max_new_trades_per_slot, self.seconds_per_driver)  # fmt: skip
        records, exits = [], []
        for driver in self.drivers:
            driver_id = driver.card.driver_id
            view = self._open(driver_id, roads.marks, session)
            tickets = open_positions(account_call(driver_id, self.books.ticket_entries.entries, driver_id))
            slot = step.run(driver, roads, view, view.open_positions, tickets)
            records.extend(slot.records)
            exits.extend(slot.exits)
        return tuple(records), tuple(exits)

    def _open(self, driver_id: str, marks, session: date):
        """Every store the fleet records into is opened by its view before any fill, the ticket ledger by the same step
        as the driver account; the driver account's view is the one the laws read."""
        views = [account_call(driver_id, store.view, driver_id, marks, session) for store in self.books.stores]
        return views[0]

    def _sealed(self, seal) -> tuple[tuple[DecisionRecord, ...], tuple[ExitRecord, ...]]:
        sealed = self.dashcam.read(seal)
        return (tuple(r for r in sealed if isinstance(r, DecisionRecord)),
                tuple(r for r in sealed if isinstance(r, ExitRecord)))  # fmt: skip

    def _ids(self) -> tuple[str, ...]:
        return tuple(d.card.driver_id for d in self.drivers)

    def _belongs(self, record) -> bool:
        """A stored record this fleet could have written: its driver is one of this fleet's, and a decision names that
        driver's card as frozen now (a file from another card version under the same key is never adopted)."""
        cards = {d.card.driver_id: d.card.card_sha256 for d in self.drivers}
        if isinstance(record, DecisionRecord):
            return cards.get(record.decision.driver_id) == record.card_sha256
        driver_id = driver_of(record.position_id) if isinstance(record, DriftRow) else record.driver_id
        return driver_id in cards

    def _finish(self, roads, records, exits, seal, rerun: bool = False) -> tuple[SlotFills, tuple[str, ...]]:
        """Rebuilt from the sealed records and the ledgers on every run, so a rerun after a crash at any point between
        the seal and the counts' commit makes what is missing and nothing twice. With the fills, the counts commit's
        refusal line, if any (judge 507.13: never silent; the run exits 1 on it)."""
        session = roads.scheduled[0].session
        if self._sealed_once(session) and self.counts.written(session, SLOT_1500):
            self.after_outcomes(session)  # write-once and same-bytes on a rerun; it may have failed the first time
            refused = self.counts.commit(session)  # a crash, or a refused push, after the counts' write
            return SlotFills({}, frozenset(), ()), refused
        if rerun and self.clock.now() > datetime.combine(session, SESSION_CLOSE, IST):
            self.counts.mark(session, SLOT_1500, LATE_RERUN)  # law 6 refuses every fill priced again now
        held = recorded(self.books, self._ids())
        slot_exits = tuple(e for e in exits if e.exit_reason != ExitReason.EXPIRY)
        fills = FillStep(self.books, self.capture_1515(session), self.rules).run(roads, records, slot_exits, seal,
                                                                      self.clock.now(), held)  # fmt: skip
        self._seal_once(session, RecordKind.OUTCOMES, outcomes_of(self.books, exits, roads.marks, self.entry_mids))
        self._seal_once(session, RecordKind.DRIFT, fills.drift)
        self.after_outcomes(session)
        counts = tuple(counts_for(r.decision, r.law_results, fills.entries.get((r.road, r.decision.driver_id)),
                                  (r.road, r.decision.driver_id) in fills.size_shared) for r in records)  # fmt: skip
        return fills, self.counts.write(session, SLOT_1500, records, counts)

    def _sealed_once(self, session: date) -> bool:
        return all(self.dashcam.find(session, SLOT_1500, kind) is not None for kind in FINISHED)  # a query: no adopting

    def _seal_once(self, session: date, kind: RecordKind, rows: tuple) -> None:
        if self.dashcam.recover(session, SLOT_1500, kind, self._belongs) is None:
            self.dashcam.seal(session, SLOT_1500, kind, rows)
