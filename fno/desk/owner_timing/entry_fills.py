"""An entry's owner-timing fill (story E8 rules 1-9 and 12): from the card's delivery time T to a fill at the due mark,
or a miss with one fixed reason. A miss is final: never filled at another mark or price.

In order: no delivered card, or a decision committed after it, misses; the clock gives the due mark (owner away,
contract expired); the mark must have passed and its on-time window closed; a blocking open trade refuses it (E4's
rule); every leg is priced at the mark inside the price cap (all or none); then funds and risk at the fill. The record
of what was decided goes first, then the fills, then the entry's outcome event, which marks it done: a rerun after a
stop part way finds the fills already in the account and finishes the same entry at the same mark without checking
funds again (its own fills would now count against it)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta

from ...constants import FILL_OPEN, OUTCOME_NOT_OPENED, OUTCOME_OPENED, OUTCOME_REFUSED
from ...intraday.slots import ON_TIME_SECONDS
from ..entries import EntryOrder
from ..execution import check_point_in_time
from ..records import DeskEvent, DeskJournal
from ..snapshot import ExecutionSnapshot, SnapshotError
from ..status import blocking_trades
from .due_fill import DueFill, PricedEntry
from .fill_risk import FillRisk
from .outcomes import DECIDED_AFTER_CARD, ENTRY, MISSED_NO_CARD, DueMark, Missed
from .timing_log import TimingLog, TimingRecord

BLOCKED = "open trade {trades} blocks new risk in {book}"
OPENED = "{legs} legs filled at the {mark:%H:%M} mark of {session}"
REPRICED = "trade {trade_id} has fills but its due mark no longer prices it ({reason}): the copy changed"
WINDOW = timedelta(seconds=ON_TIME_SECONDS)  # a mark is read once its copy's on-time window has closed


class OwnerTimingEntries:
    def __init__(self, due_fill: DueFill, risk: FillRisk, log: TimingLog, view: str, reaction_minutes: int,
                 clock: Callable[[], datetime]):  # fmt: skip
        self.due_fill, self.risk, self.log, self.view = due_fill, risk, log, view
        self.reaction, self.clock = reaction_minutes, clock

    def apply(self, order: EntryOrder, card_time: datetime | None, journal: DeskJournal) -> str | None:
        """The entry's outcome reason once decided and recorded; None while its due mark has not passed."""
        trade_id = order.proposal.trade_id
        if card_time is None:
            return self._event(journal, order, OUTCOME_NOT_OPENED, MISSED_NO_CARD)
        if order.decided_at >= card_time:
            return self._decided(journal, order, card_time, None, Missed(DECIDED_AFTER_CARD))
        due = self.due_fill.schedule(order, card_time)
        if isinstance(due, Missed):
            return self._decided(journal, order, card_time, None, due)
        if due.mark + WINDOW > self.clock():
            return None
        rerun = bool(journal.records.fill_rows(trade_id))  # fills written by a stopped run: finish, never re-check
        blocked = [] if rerun else blocking_trades(journal.records)
        if blocked:
            reason = BLOCKED.format(trades="; ".join(blocked), book=order.book)
            return self._decided(journal, order, card_time, due, Missed(reason), OUTCOME_REFUSED)
        priced = self.due_fill.price(order, due, journal.records.fill_rows())
        if isinstance(priced, Missed):
            if rerun:
                raise SnapshotError(REPRICED.format(trade_id=trade_id, reason=priced.reason))
            return self._decided(journal, order, card_time, due, priced)
        check_point_in_time(priced.maker.snapshot, self.clock())
        miss = "" if rerun else self.risk.miss(order, priced)
        if miss:
            return self._decided(journal, order, card_time, due, Missed(miss), priced=priced)
        return self._fill(journal, order, card_time, priced)

    def _fill(self, journal: DeskJournal, order: EntryOrder, card_time: datetime, priced: PricedEntry) -> str:
        reason = OPENED.format(legs=len(priced.quotes), mark=priced.due.mark, session=priced.due.session)
        snapshot = priced.maker.snapshot
        self.log.record(self._record(order, card_time, priced.due, snapshot, OUTCOME_OPENED, reason))
        for quote in priced.quotes:  # protection first (E4's order)
            journal.record_fill(priced.maker.record(quote, FILL_OPEN))
        return self._event(journal, order, OUTCOME_OPENED, reason, snapshot)

    def _decided(self, journal, order: EntryOrder, card_time: datetime, due: DueMark | None, missed: Missed,
                 outcome: str = OUTCOME_NOT_OPENED, priced: PricedEntry | None = None) -> str:  # fmt: skip
        """A miss, with the copy it was read from when there was one, so its record can be checked again."""
        snapshot = priced.maker.snapshot if priced else missed.copy
        self.log.record(self._record(order, card_time, due, snapshot, outcome, missed.reason))
        return self._event(journal, order, outcome, missed.reason, snapshot)

    def _record(self, order: EntryOrder, card_time: datetime, due: DueMark | None,
                snapshot: ExecutionSnapshot | None, outcome: str, reason: str) -> TimingRecord:  # fmt: skip
        return TimingRecord(
            order.book, self.view, order.proposal.trade_id, ENTRY, self.reaction, card_time,
            due.mark if due else None, due.mark if due and snapshot else None,
            snapshot.snapshot_id if snapshot else "", snapshot.sha256 if snapshot else "", outcome, reason,
        )  # fmt: skip

    def _event(self, journal: DeskJournal, order: EntryOrder, outcome: str, reason: str,
               snapshot: ExecutionSnapshot | None = None) -> str:  # fmt: skip
        trade_id = order.proposal.trade_id
        day = snapshot.day if snapshot else self.clock().date()
        journal.record_event(DeskEvent(
            f"{trade_id}:{outcome}", day, order.book, order.strategy, trade_id, order.decision_id,
            snapshot.snapshot_id if snapshot else "", snapshot.sha256 if snapshot else "", outcome, reason,
        ))  # fmt: skip
        return reason
