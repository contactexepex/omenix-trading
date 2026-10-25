"""The daily run's hand-over of an entry to the owner-timing fill (story E8 rules 1 and 10): in place of E4's fill at
the execution snapshot, the order is kept as decided and the verdict account records `entry_pending`; the
owner-timing step fills that order at the next session's due mark from the card's delivery time.

The daily run's own gates still run first (C3, C4's pass, the decision on time, a book blocked after unreviewed
exits). E4's gate on the decision runs unchanged, through E4's own `refusal`, except its demand for a complete
execution capture (judge 203 condition 2): no owner acts on that capture, and the due mark's copy is checked leg by
leg when the entry fills. A refused entry is final, as in E4."""

from __future__ import annotations

from dataclasses import replace

from ...checks.data_checks import CheckReport
from ...constants import OUTCOME_ENTRY_PENDING, OUTCOME_REFUSED
from ..entries import EntryFiller, EntryOrder, EntryResult, refusal
from ..records import DeskEvent, DeskJournal
from ..snapshot import ExecutionSnapshot
from ..status import ENTRY_OUTCOMES, blocking_trades
from .order_record import KeptOrders

HANDED_OVER = "handed to the owner-timing fill: R = {minutes} minutes after the card's delivery"


class PendingEntries(EntryFiller):
    def __init__(self, reaction_minutes: int, orders: KeptOrders):
        self.reaction, self.orders = reaction_minutes, orders

    def enter(self, order: EntryOrder, snapshot: ExecutionSnapshot, journal: DeskJournal, checks: CheckReport
              ) -> EntryResult:  # fmt: skip
        trade_id = order.proposal.trade_id
        done = [r for r in journal.records.event_rows(trade_id)
                if r["outcome"] in (*ENTRY_OUTCOMES, OUTCOME_ENTRY_PENDING)]  # fmt: skip
        if done:
            return EntryResult(trade_id, done[0]["outcome"], done[0]["reason"])
        reason = refusal(order, replace(snapshot, complete=True), blocking_trades(journal.records))
        outcome = OUTCOME_REFUSED if reason else OUTCOME_ENTRY_PENDING
        if not reason:
            self.orders.keep(order)  # first: an entry is never pending without the order it will fill
        reason = reason or HANDED_OVER.format(minutes=self.reaction)
        journal.record_event(DeskEvent(
            f"{trade_id}:{outcome}", snapshot.day, order.book, order.strategy, trade_id, order.decision_id,
            snapshot.snapshot_id, snapshot.sha256, outcome, reason,
        ))  # fmt: skip
        return EntryResult(trade_id, outcome, reason)
