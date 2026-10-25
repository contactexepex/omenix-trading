"""In-memory fakes of every school port (story MS-P1a), for the parts' tests. Each passes the conformance checks in
`tests/school/contracts/conformance.py`, as every real class must. No production path imports this module."""

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date, datetime

from .constants import (
    SIDE_BUY,
    SIDE_SELL,
    ClosureReason,
    ExitReason,
    ExitState,
    NoTradeReason,
    OptionKind,
    Outcome,
    RecordKind,
    RefusalReason,
    RoadCode,
)
from .contracts.accounts import (
    FilledLeg,
    FillResult,
    LedgerEntry,
    SealedDecision,
    SettlementPrice,
    SettlementUnavailable,
)
from .contracts.dashcam import Belongs, ReplayConflict
from .contracts.decisions import Decision, DriverCard, LegSpec, OpenPosition, Proposal, SpotPoint
from .contracts.reports import Banner, SectionText
from .contracts.roads import ROADS_BY_CODE, RoadDay
from .contracts.safety import AccountView, LawResult
from .contracts.seal import Seal, StaleSeal
from .contracts.slot_file import SlotRecord, decode_slot_file, encode_slot_file
from .contracts.snapshot import SlotSnapshot, SnapshotUnavailable
from .dashcam.adoption import adoptable


@dataclass
class FakeRoadCatalogue:
    days: dict[date, tuple[RoadDay, ...]] = field(default_factory=dict)

    def day(self, session: date) -> tuple[RoadDay, ...]:
        return self.days.get(session, ())


@dataclass
class FakeSnapshotSource:
    snapshots: dict[tuple, SlotSnapshot] = field(default_factory=dict)  # (road code, session) -> snapshot

    def for_road(self, road_day: RoadDay) -> SlotSnapshot:
        if not road_day.status.open:
            raise SnapshotUnavailable(road_day.status.closed_by)
        found = self.snapshots.get((road_day.road.code, road_day.session))
        if found is None:
            raise SnapshotUnavailable(ClosureReason.CAPTURE_MISSING)
        return found


@dataclass
class FakeDriver:
    """Proposes its scripted proposal on every road (no trade without one) and closes on its scripted exit reason."""

    card: DriverCard
    proposal: Proposal | None = None
    exit_reason: ExitReason | None = None

    def decide(self, road_day: RoadDay, snapshot: SlotSnapshot, history: tuple[SpotPoint, ...],
               positions: tuple[OpenPosition, ...]) -> Decision:  # fmt: skip
        road, session = road_day.road.code, road_day.session
        if self.proposal is None:
            return Decision(self.card.driver_id, road, session, Outcome.NO_TRADE, NoTradeReason.RULE_NOT_FIRED)
        return Decision(self.card.driver_id, road, session, Outcome.TRADE, "", self.proposal)

    def review_exit(self, position: OpenPosition, snapshot: SlotSnapshot,
                    history: tuple[SpotPoint, ...]) -> ExitReason | None:  # fmt: skip
        return self.exit_reason


@dataclass
class FakeMaxLossLaw:
    limit: float
    name: str = "max_loss"

    def check(self, proposal: Proposal, account: AccountView, snapshot: SlotSnapshot, session: date) -> LawResult:
        passed = proposal.max_loss <= self.limit
        return LawResult(self.name, passed, None if passed else RefusalReason.MAX_LOSS, self.limit, proposal.max_loss)


@dataclass
class FakeAccounts:
    """Cash only: open positions are valued at zero (no marking), which is all a fake needs."""

    capital: float
    ledgers: dict[str, list[LedgerEntry]] = field(default_factory=dict)
    opened: set[str] = field(default_factory=set)  # accounts a view has opened: a record before one is refused

    def view(self, driver_id: str, marks: Mapping[RoadCode, SlotSnapshot], session: date) -> AccountView:
        self.opened.add(driver_id)
        entries = self.ledgers.get(driver_id, [])
        closed = {e.position.position_id for e in entries if e.closes}
        open_ = tuple(e.position for e in entries if not e.closes and e.position.position_id not in closed)
        cash = self.capital + sum(e.fill.cash for e in entries)
        today = tuple(p for p in open_ if p.opened == session)
        return AccountView(driver_id, self.capital, cash, cash, max(cash, self.capital), 0.0, today, open_, None, None)

    def entries(self, driver_id: str) -> tuple[LedgerEntry, ...]:
        return tuple(self.ledgers.get(driver_id, ()))

    def record(self, driver_id: str, entry: LedgerEntry) -> None:
        if driver_id not in self.opened:
            raise ValueError(f"{driver_id}: a fill before the account's first view")  # as d's store refuses it
        ledger = self.ledgers.setdefault(driver_id, [])
        if entry not in ledger:
            ledger.append(entry)


@dataclass
class FakeFills:
    """Touch fills with zero charges; settlement at intrinsic from the settlement source."""

    settlements: "FakeSettlementSource" = field(default_factory=lambda: FakeSettlementSource())

    def enter(self, sealed: SealedDecision, snapshot: SlotSnapshot, seal: Seal, at: datetime) -> FillResult:
        proposal = sealed.decision.proposal
        return self._fill(
            proposal.legs, proposal.lot, snapshot, sealed.file_sha256, seal, at, RefusalReason.MISSING_QUOTE
        )

    def exit(self, position: OpenPosition, snapshot: SlotSnapshot, file_sha256: str, seal: Seal,
             at: datetime) -> FillResult:  # fmt: skip
        flip = {SIDE_BUY: SIDE_SELL, SIDE_SELL: SIDE_BUY}
        closing = tuple(LegSpec(leg.key, flip[leg.side], leg.lots) for leg in position.legs)
        return self._fill(closing, position.lot, snapshot, file_sha256, seal, at, ExitState.EXIT_WAITING_QUOTE)

    def settle(self, position: OpenPosition, expiry: date) -> FillResult:
        try:
            settlement = self.settlements.price(ROADS_BY_CODE[position.road].underlying, expiry)
        except SettlementUnavailable:
            return FillResult(state=ExitState.SETTLEMENT_NEEDED)
        flip = {SIDE_BUY: SIDE_SELL, SIDE_SELL: SIDE_BUY}
        legs = tuple(FilledLeg(leg.key, flip[leg.side], leg.lots * position.lot, _intrinsic(leg, settlement.price), 0.0)
                     for leg in position.legs if leg.key.expiry == expiry)  # fmt: skip
        at = datetime.fromisoformat(f"{expiry}T15:30:00+05:30")
        return FillResult(legs, filled_at=at, rests_on=settlement.file_sha256)

    @staticmethod
    def _fill(legs, lot, snapshot, file_sha256, seal, at, missing) -> FillResult:
        """A live fill needs a measured displayed size (judge 506): an unmeasured quote refuses the entry by name, and
        an exit on one waits, as on a missing quote."""
        if not seal.covers(file_sha256, at):
            return FillResult(refused=(RefusalReason.STALE_SEAL,))
        filled = []
        for leg in legs:
            quote = snapshot.quote(leg.key)
            if quote is not None and not quote.sizes_measured and not isinstance(missing, ExitState):
                return FillResult(refused=(RefusalReason.SIZE_NOT_MEASURED,))
            if quote is None or not quote.two_sided or not quote.sizes_measured:
                return FillResult(state=missing) if isinstance(missing, ExitState) else FillResult(refused=(missing,))
            price = quote.ask if leg.side == SIDE_BUY else quote.bid
            filled.append(FilledLeg(leg.key, leg.side, leg.lots * lot, price, 0.0))
        return FillResult(tuple(filled), filled_at=at, rests_on=file_sha256)


def _intrinsic(leg: LegSpec, settlement: float) -> float:
    if leg.key.kind == OptionKind.CALL:
        return max(settlement - leg.key.strike, 0.0)
    return max(leg.key.strike - settlement, 0.0)


@dataclass
class FakeDashcam:
    files: dict[tuple, bytes] = field(default_factory=dict)
    pushed_at: datetime | None = None  # None: the session's slot time
    stored: dict[tuple, bytes] = field(default_factory=dict)  # on "Drive" with no receipt: a run stopped between

    def seal(self, session: date, slot: str, kind: RecordKind, records: tuple[SlotRecord, ...]) -> Seal:
        key, payload = (session, slot, kind), encode_slot_file(records)
        held = self.files.get(key, self.stored.get(key))  # Drive refuses other bytes, receipt or not
        if held is not None and held != payload:
            raise ReplayConflict(f"{session} {slot} {kind}")
        self.stored.pop(key, None)
        self.files[key] = payload
        return self._seal(session, slot, kind, payload)

    def _seal(self, session: date, slot: str, kind: RecordKind, payload: bytes) -> Seal:
        path = f"school/dashcam/{session:%Y/%m/%d}/{slot.replace(':', '')}.{kind}.jsonl.gz"
        when = self.pushed_at or datetime.fromisoformat(f"{session}T{slot}:00+05:30")
        return Seal(path, hashlib.sha256(payload).hexdigest(), when, "fake")

    def find(self, session: date, slot: str, kind: RecordKind) -> Seal | None:
        payload = self.files.get((session, slot, kind))
        return None if payload is None else self._seal(session, slot, kind, payload)

    def recover(self, session: date, slot: str, kind: RecordKind, belongs: Belongs) -> Seal | None:
        key = (session, slot, kind)
        if key not in self.files and key in self.stored:
            adoptable(self.stored[key], session, slot, kind, belongs)
            self.files[key] = self.stored.pop(key)
        return self.find(session, slot, kind)

    def read(self, seal: Seal) -> tuple[SlotRecord, ...]:
        found = [data for data in self.files.values() if hashlib.sha256(data).hexdigest() == seal.sha256]
        if not found:
            raise StaleSeal(seal.path)
        return decode_slot_file(found[0])


@dataclass
class FakeSection:
    title: str = "Today"

    def render(self, session: date) -> SectionText:
        return SectionText(self.title, (f"{session}",), Banner.AMBER)


@dataclass
class FakeSettlementSource:
    prices: dict[tuple[str, date], SettlementPrice] = field(default_factory=dict)

    def price(self, underlying: str, expiry: date) -> SettlementPrice:
        if (underlying, expiry) not in self.prices:
            raise SettlementUnavailable(f"{underlying} {expiry}")
        return self.prices[(underlying, expiry)]
