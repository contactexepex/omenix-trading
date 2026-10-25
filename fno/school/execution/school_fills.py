"""The school's fill port (stories 3.3 law 6 and 3.6): a sealed decision fills at its own snapshot's touch, ask to buy
and bid to sell, every leg or none, only after its seal; an exit closes every leg at the touch or waits; an expiring
position settles at intrinsic against the index's final settlement price. Prices, sizes and charges are E4's
(`price_leg`, E4c/E4d's checks, `FillMaker` with C1's charges, `closing_quotes`), so the school adds no second rule.

A seal or fill after the session's 15:30 close is `stale_seal` (law 6): a late record never trades at an old touch.
Never partial (story 3.6): an exit with any leg it cannot close now fills nothing and waits (`exit_waiting_quote`),
so a position is never left short without its protection and never priced from anything but its road's snapshot.
Sizes reach E4 through `QuoteRules`: `LIVE` here and in `wiring.py`; practice rules only from `practice_wiring.py`."""

from collections.abc import Mapping
from datetime import date, datetime

from ...constants import FILL_CLOSE, FILL_OPEN
from ...desk.execution import FillMaker, closing_quotes
from ...desk.pricing import LegQuote, price_leg
from ...desk.settlement import SETTLEMENT_TIME as SESSION_CLOSE
from ...desk.snapshot import ExecutionSnapshot
from ...models import IST
from ..constants import ExitState, Outcome, RefusalReason
from ..contracts.accounts import FilledLeg, FillResult, IndexSettlementSource, SealedDecision
from ..contracts.decisions import LegSpec, OpenPosition
from ..contracts.roads import ROADS_BY_CODE
from ..contracts.seal import Seal
from ..contracts.snapshot import ContractKey, SlotSnapshot
from .desk_view import desk_leg, execution_snapshot, school_legs, size_unmeasured
from .entry_gate import entry_refusals
from .quote_rules import LIVE, QuoteRules
from .settlement_fills import settlement_fill

FILLED_OUTCOMES = (Outcome.TRADE, Outcome.TICKET)  # a ticket is priced by the same rule (response 327 item 1)


class SchoolFills:
    def __init__(self, charges: Mapping[str, float], settlements: IndexSettlementSource, rules: QuoteRules = LIVE):
        self.charges, self.settlements, self.rules = dict(charges), settlements, rules

    def enter(self, sealed: SealedDecision, snapshot: SlotSnapshot, seal: Seal, at: datetime) -> FillResult:
        decision = sealed.decision
        if decision.outcome not in FILLED_OUTCOMES:
            raise ValueError(f"a {decision.outcome} decision never fills ({decision.driver_id} {decision.road})")
        _same_slot(snapshot, decision.road, decision.session, at)
        if not _sealed_in_time(seal, sealed.file_sha256, snapshot, at):
            return FillResult(refused=(RefusalReason.STALE_SEAL,))
        proposal, underlying = decision.proposal, ROADS_BY_CODE[decision.road].underlying
        if len({leg.key for leg in proposal.legs}) != len(proposal.legs):
            raise ValueError(f"{decision.driver_id}: a proposal names a contract twice (the laws refuse it)")
        desk = execution_snapshot(snapshot, underlying, self.rules)
        legs = school_legs(underlying, proposal.legs, proposal.lot)
        refused = entry_refusals(desk, legs, {}, size_unmeasured(snapshot, underlying, self.rules))
        if refused:
            return FillResult(refused=refused)
        maker = self._maker(desk, decision.driver_id, sealed.file_sha256)
        filled = tuple(self._opened(maker, desk, underlying, leg, proposal.lot) for leg in proposal.legs)
        return FillResult(filled, filled_at=at, rests_on=sealed.file_sha256)

    def exit(self, position: OpenPosition, snapshot: SlotSnapshot, file_sha256: str, seal: Seal,
             at: datetime) -> FillResult:  # fmt: skip
        _same_slot(snapshot, position.road, snapshot.session, at)
        if snapshot.session < position.opened:
            raise ValueError(f"{position.position_id} cannot close at {snapshot.session}, before it opened")
        if not _sealed_in_time(seal, file_sha256, snapshot, at):
            return FillResult(refused=(RefusalReason.STALE_SEAL,))
        legs = school_legs(ROADS_BY_CODE[position.road].underlying, position.legs, position.lot)
        desk = execution_snapshot(snapshot, ROADS_BY_CODE[position.road].underlying, self.rules)
        closing, pending = closing_quotes(desk, [(leg.desk, leg.units) for leg in legs])
        if pending:
            return FillResult(state=ExitState.EXIT_WAITING_QUOTE)
        by_contract = {leg.desk.contract: leg for leg in legs}
        maker = self._maker(desk, position.driver_id, file_sha256)
        filled = tuple(self._filled(maker, q, by_contract[q.leg.contract].spec.key, FILL_CLOSE) for q in closing)
        return FillResult(filled, filled_at=at, rests_on=file_sha256)

    def settle(self, position: OpenPosition, expiry: date) -> FillResult:
        return settlement_fill(position, expiry, self.settlements, self.charges)

    def _maker(self, desk: ExecutionSnapshot, driver_id: str, file_sha256: str) -> FillMaker:
        return FillMaker(driver_id, driver_id, file_sha256, file_sha256, desk, self.charges)

    def _opened(self, maker: FillMaker, desk: ExecutionSnapshot, underlying: str, leg: LegSpec, lot: int) -> FilledLeg:
        opening = desk_leg(underlying, leg)
        return self._filled(maker, price_leg(desk, opening, leg.side, leg.lots * lot), leg.key, FILL_OPEN)

    @staticmethod
    def _filled(maker: FillMaker, quote: LegQuote, key: ContractKey, action: str) -> FilledLeg:
        fill = maker.fill(quote, action)
        return FilledLeg(key, quote.side, quote.units, quote.price, sum(fill.charges.values()))


def _sealed_in_time(seal: Seal, file_sha256: str, snapshot: SlotSnapshot, at: datetime) -> bool:
    """Law 6: the seal names this file, was pushed by the fill, and both happen by the session's close: a decision
    sealed or filled later would trade at an old touch after seeing the market move (no record, no trade)."""
    close = datetime.combine(snapshot.session, SESSION_CLOSE, IST)
    return seal.covers(file_sha256, at) and at <= close


def _same_slot(snapshot: SlotSnapshot, road, session: date, at: datetime) -> None:
    """A fill is priced only from its own road's snapshot of its session, and never before that snapshot finished."""
    if (snapshot.road, snapshot.session) != (road, session):
        raise ValueError(f"snapshot {snapshot.snapshot_id} is {snapshot.road} {snapshot.session}, not {road} {session}")
    if at.tzinfo is None or at < snapshot.finished_at:
        raise ValueError(f"a fill at {at} would precede its snapshot {snapshot.snapshot_id}'s finish")
