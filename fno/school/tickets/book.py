"""The ticket book (story MS-P1f): opens, closes and settles tickets with the same fill port as trades, after the
same laws (account limits relaxed), and records them only in the ticket ledger, never in a driver's account."""

from dataclasses import dataclass
from datetime import date, datetime

from ..constants import ExitReason, Outcome
from ..contracts.accounts import AccountPort, FillPort, FillResult, LedgerEntry, SealedDecision
from ..contracts.decisions import OpenPosition
from ..contracts.records import DecisionRecord
from ..contracts.seal import Seal
from ..contracts.snapshot import SlotSnapshot
from .rules import first_binding_refusal


def ticket_id(sealed: SealedDecision) -> str:
    decision = sealed.decision
    return f"ticket:{decision.driver_id}:{decision.road}:{decision.session}"


def _position(sealed: SealedDecision, fill: FillResult) -> OpenPosition:
    decision, proposal = sealed.decision, sealed.decision.proposal
    return OpenPosition(ticket_id(sealed), decision.driver_id, decision.road, proposal.structure, proposal.legs,
                        proposal.lot, decision.session, fill.cash, proposal.max_loss)  # fmt: skip


@dataclass(frozen=True)
class TicketLedger:
    """Its own type, so the composition root cannot hand a driver's account to the ticket book by mistake."""

    store: AccountPort  # an account store on its own root, apart from every driver account


@dataclass(frozen=True)
class TicketBook:
    fills: FillPort
    ledger: TicketLedger

    def enter(self, record: DecisionRecord, file_sha256: str, snapshot: SlotSnapshot, seal: Seal,
              at: datetime) -> FillResult:  # fmt: skip
        """`price`, then `open` when it filled."""
        fill = self.price(record, file_sha256, snapshot, seal, at)
        if fill.filled:
            self.open(record, file_sha256, fill)
        return fill

    def price(self, record: DecisionRecord, file_sha256: str, snapshot: SlotSnapshot, seal: Seal,
              at: datetime) -> FillResult:  # fmt: skip
        """`record`: the ticket's sealed decision record, read back from the dashcam file `file_sha256`; its own law
        results decide (judge 490). A law that binds a ticket refuses it before any fill; missing results raise.
        Records nothing: the fleet records a ticket only when the shared displayed size can serve it (MS-P1j)."""
        sealed = SealedDecision(record.decision, file_sha256)
        if sealed.decision.outcome != Outcome.TICKET:
            raise ValueError("the ticket book enters tickets only")
        binding = first_binding_refusal(record.law_results)
        if binding is not None:
            return FillResult(refused=(binding,))
        return self.fills.enter(sealed, snapshot, seal, at)

    def open(self, record: DecisionRecord, file_sha256: str, fill: FillResult) -> None:
        sealed = SealedDecision(record.decision, file_sha256)
        if sealed.decision.outcome != Outcome.TICKET or not fill.filled:
            raise ValueError("the ticket book opens filled tickets only")
        entry = LedgerEntry(_position(sealed, fill), fill, closes=False, recorded_for=sealed.decision.session)
        self.ledger.store.record(sealed.decision.driver_id, entry)

    def exit(self, position: OpenPosition, reason: ExitReason, snapshot: SlotSnapshot, file_sha256: str, seal: Seal,
             at: datetime) -> FillResult:  # fmt: skip
        fill = self.fills.exit(position, snapshot, file_sha256, seal, at)
        return self.close(position, fill, reason, snapshot.session)

    def settle(self, position: OpenPosition, expiry: date, session: date | None = None) -> FillResult:
        """`session`: the session whose run settles it (`LedgerEntry.recorded_for`)."""
        return self.close(position, self.fills.settle(position, expiry), ExitReason.EXPIRY, session)

    def close(self, position: OpenPosition, fill: FillResult, reason: ExitReason,
              session: date | None = None) -> FillResult:  # fmt: skip
        """Records the closing when `fill` filled (the fleet's exits after the shared size, settlement here)."""
        if fill.filled:
            closing = LedgerEntry(position, fill, closes=True, exit_reason=reason, recorded_for=session)
            self.ledger.store.record(position.driver_id, closing)
        return fill
