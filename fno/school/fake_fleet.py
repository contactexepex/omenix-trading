"""The fake fleet (story MS-P1a, for MS-P1i's harness): every fake driver on every catalogued road for one session,
in the real order (decide, laws, seal, fill), with no tickets, exits or marks. MS-P1j's real fleet passes the same
conformance check. No production path imports this module."""

from dataclasses import dataclass, replace
from datetime import date

from .constants import SCHOOL_OFF_LINE, SLOT_1500, ClosureReason, Outcome, RecordKind
from .contracts.accounts import AccountPort, FillPort, LedgerEntry, SealedDecision
from .contracts.clock import Clock
from .contracts.dashcam import DashcamStore
from .contracts.decisions import Decision, Driver, OpenPosition
from .contracts.fleet import RunMode, SessionRun
from .contracts.records import DecisionRecord, WitnessedQuote
from .contracts.roads import RoadCatalogue, RoadDay
from .contracts.safety import SafetyLaw
from .contracts.snapshot import SlotSnapshot, SnapshotSource, SnapshotUnavailable


@dataclass
class FakeFleet:
    enabled: bool
    catalogue: RoadCatalogue
    snapshots: SnapshotSource
    drivers: tuple[Driver, ...]
    laws: tuple[SafetyLaw, ...]
    accounts: AccountPort
    fills: FillPort
    dashcam: DashcamStore
    clock: Clock

    def run(self, session: date, mode: RunMode) -> SessionRun:
        if not self.enabled:
            return SessionRun(session, mode, SCHOOL_OFF_LINE)
        sealed = self.dashcam.find(session, SLOT_1500, RecordKind.DECISIONS)
        if sealed is not None:  # a rerun: the session is already sealed and filled
            records = tuple(r for r in self.dashcam.read(sealed) if isinstance(r, DecisionRecord))
            return SessionRun(session, mode, "", records, sealed)
        planned = [
            self._decide(road_day, driver)
            for road_day in self.catalogue.day(session)
            for driver in self.drivers
            if road_day.road.code in driver.card.roads  # only the card's own roads, as the real fleet schedules
        ]
        records = tuple(record for record, _ in planned)
        if not records:
            return SessionRun(session, mode, "")
        seal = self.dashcam.seal(session, SLOT_1500, RecordKind.DECISIONS, records)
        fills = tuple(self._fill(record.decision, snapshot, seal) for record, snapshot in planned
                      if record.decision.outcome == Outcome.TRADE)  # fmt: skip
        return SessionRun(session, mode, "", records, seal, fills)

    def _decide(self, road_day: RoadDay, driver: Driver) -> tuple[DecisionRecord, SlotSnapshot | None]:
        code, session = road_day.road.code, road_day.session
        try:
            snapshot = self.snapshots.for_road(road_day)
            if not all(q.sizes_measured for q in snapshot.quotes.values()):  # never traded on live (judge 506)
                raise SnapshotUnavailable(ClosureReason.SIZES_NOT_MEASURED, "a quote with no measured size")
        except SnapshotUnavailable as closed:
            decision = Decision(driver.card.driver_id, code, session, Outcome.ROAD_CLOSED, closed.reason)
            return DecisionRecord(
                session, SLOT_1500, code, driver.card.card_sha256, "", "", closed.reason, decision
            ), None
        decision = driver.decide(road_day, snapshot, (), ())
        results = ()
        if decision.outcome == Outcome.TRADE:
            view = self.accounts.view(decision.driver_id, {code: snapshot}, session)
            results = tuple(law.check(decision.proposal, view, snapshot, session) for law in self.laws)
            refusals = [r.reason for r in results if not r.passed]
            if refusals:
                decision = replace(decision, outcome=Outcome.REFUSED, reason=refusals[0])
        legs = decision.proposal.legs if decision.proposal else ()
        witnessed = tuple(WitnessedQuote(leg.key, snapshot.quote(leg.key)) for leg in legs if snapshot.quote(leg.key))
        record = DecisionRecord(session, SLOT_1500, code, driver.card.card_sha256, snapshot.snapshot_id,
                                snapshot.sha256, None, decision, results, witnessed)  # fmt: skip
        return record, snapshot

    def _fill(self, decision: Decision, snapshot: SlotSnapshot, seal):
        fill = self.fills.enter(SealedDecision(decision, seal.sha256), snapshot, seal, self.clock.now())
        if fill.filled:
            proposal = decision.proposal
            position = OpenPosition(f"{decision.driver_id}:{decision.road}:{decision.session}", decision.driver_id,
                                    decision.road, proposal.structure, proposal.legs, proposal.lot, decision.session,
                                    fill.cash, proposal.max_loss)  # fmt: skip
            self.accounts.record(decision.driver_id, LedgerEntry(position, fill, closes=False))
        return fill
