"""After the seal (story MS-P1j; order: seal, fills, exits): every sealed trade fills at its road's touch, every ticket
through the ticket book's own laws; then the exits the cards called. Per road, MS-P1f's `allocate` serves the slot's
fills against the displayed size: entries first (accounts, then tickets, each in a seeded order), exits only from
what is left (MS-P1d limit 2). Only what it can serve is recorded: an account entry it cannot is `size_shared` and
stays in every denominator, a ticket it cannot is not opened, an exit it cannot waits for a later slot. So no ledger
ever holds a fill the shared size could not serve, and no outcome rests on one.

The step is rebuilt from the sealed records and the ledgers on every run: a fill already recorded is read back, not
made again, so a rerun after a crash records only what is missing and serves the size exactly as one clean run would.
NIFTY entries get their 15:15 drift rows, never a fill."""

from dataclasses import dataclass
from datetime import datetime

from ...desk.snapshot import ExecutionSnapshot
from ..constants import SLOT_1500, Outcome
from ..contracts.accounts import FillResult, LedgerEntry, SealedDecision
from ..contracts.records import DecisionRecord, DriftRow, ExitRecord
from ..contracts.seal import Seal
from ..execution.drift import drift_rows
from ..execution.quote_rules import QuoteRules
from ..tickets.shared_size import OwnedFill, allocate
from .books import Books, account_call
from .ledgers import Recorded, ledger_id
from .outcomes import TICKET_PREFIX
from .running_view import opened_position, position_id
from .slot import SlotRoads


@dataclass(frozen=True)
class SlotFills:
    entries: dict[tuple, FillResult]  # (road, driver id) -> the entry fill of its sealed trade or ticket
    size_shared: frozenset[tuple]  # (road, driver id) of the account entries the displayed size could not serve
    drift: tuple[DriftRow, ...]

    @property
    def fills(self) -> tuple[FillResult, ...]:
        return tuple(self.entries.values())


@dataclass(frozen=True)
class FillStep:
    books: Books
    capture_1515: ExecutionSnapshot | None
    rules: QuoteRules  # the fleet's own quote rules (no default: a step never assumes the live ones)

    def run(self, roads: SlotRoads, records: tuple[DecisionRecord, ...], exits: tuple[ExitRecord, ...], seal: Seal,
            at: datetime, held: Recorded) -> SlotFills:  # fmt: skip
        """`exits`: the slot's exit records (not settlements); `held`: the ledgers as they stood before this step."""
        marks = roads.marks
        entered = [(r, held.openings.get(ledger_id(r)) or self._price(r, marks[r.road], seal, at)) for r in records
                   if r.decision.outcome in (Outcome.TRADE, Outcome.TICKET)]  # fmt: skip
        closing = [(e, held.closings.get(e.position_id) or self._exit_fill(e, marks[e.road], seal, at, held))
                   for e in exits if e.position_id in held.closings or e.position_id in held.still_open]  # fmt: skip
        unservable = self._unservable(entered, closing, marks)
        served = [(r, f) for r, f in entered if f.filled and (r.decision.driver_id, f) not in unservable]
        for record, fill in served:
            if ledger_id(record) not in held.openings:
                self._open(record, fill, seal)
        for exit_, fill in closing:
            if fill.filled and (exit_.driver_id, fill) not in unservable and exit_.position_id not in held.closings:
                self._close(exit_, fill, held)
        shared = frozenset(_key(r) for r, f in entered if r.decision.outcome == Outcome.TRADE and f.filled
                           and (r.decision.driver_id, f) in unservable)  # fmt: skip
        session = roads.scheduled[0].session
        drift = tuple(
            row for r, f in served if r.decision.outcome == Outcome.TRADE for row in self._drift(session, r, f)
        )
        return SlotFills({_key(r): f for r, f in entered}, shared, drift)

    def _unservable(self, entered, closing, marks) -> frozenset[tuple[str, FillResult]]:
        owned: dict = {}
        for record, fill in entered:
            is_ticket = record.decision.outcome == Outcome.TICKET
            owned.setdefault(record.road, []).append(OwnedFill(record.decision.driver_id, fill, is_ticket))
        for exit_, fill in closing:
            is_ticket = exit_.position_id.startswith(TICKET_PREFIX)
            owned.setdefault(exit_.road, []).append(OwnedFill(exit_.driver_id, fill, is_ticket, is_exit=True))
        allocations = [allocate(fills, marks[road], SLOT_1500, self.rules) for road, fills in owned.items()]
        return frozenset().union(*(a.unservable_fills for a in allocations))

    def _price(self, record: DecisionRecord, snapshot, seal: Seal, at: datetime) -> FillResult:
        if record.decision.outcome == Outcome.TICKET:
            return self.books.tickets.price(record, seal.sha256, snapshot, seal, at)
        return self.books.fills.enter(SealedDecision(record.decision, seal.sha256), snapshot, seal, at)

    def _exit_fill(self, exit_: ExitRecord, snapshot, seal: Seal, at: datetime, held: Recorded) -> FillResult:
        return self.books.fills.exit(held.still_open[exit_.position_id], snapshot, seal.sha256, seal, at)

    def _open(self, record: DecisionRecord, fill: FillResult, seal: Seal) -> None:
        driver_id = record.decision.driver_id
        if record.decision.outcome == Outcome.TICKET:
            account_call(driver_id, self.books.tickets.open, record, seal.sha256, fill)
        else:
            entry = LedgerEntry(opened_position(record.decision, fill.cash), fill, closes=False,
                                recorded_for=record.session)  # fmt: skip
            account_call(driver_id, self.books.accounts.record, driver_id, entry)

    def _close(self, exit_: ExitRecord, fill: FillResult, held: Recorded) -> None:
        position = held.still_open[exit_.position_id]
        if exit_.position_id.startswith(TICKET_PREFIX):
            account_call(position.driver_id, self.books.tickets.close, position, fill, exit_.exit_reason, exit_.session)
        else:
            closing = LedgerEntry(
                position, fill, closes=True, exit_reason=exit_.exit_reason, recorded_for=exit_.session
            )
            account_call(position.driver_id, self.books.accounts.record, position.driver_id, closing)

    def _drift(self, session, record: DecisionRecord, fill: FillResult) -> tuple[DriftRow, ...]:
        return drift_rows(session, position_id(record.decision), record.road, fill, self.capture_1515)


def _key(record: DecisionRecord) -> tuple:
    return record.road, record.decision.driver_id
