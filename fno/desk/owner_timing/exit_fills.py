"""An exit's owner-timing fill (story E8 rules 1-3, 7, 9 and 12): from the exit alert's delivery time T, the position
closes at the due mark's valid quotes, short legs bought back first and protection sold last (E4's order). A leg
without a valid quote waits and is retried at each following mark the owner is present; an exit is never limited and
never missed. A mark after a leg's expiry is left to E7's settlement in the daily run's exit review. A pending exit is
recorded and alerted once per run, not once per mark."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime

from ...constants import FILL_CLOSE, OUTCOME_CLOSED, OUTCOME_PENDING_EXIT
from ..execution import FillMaker, check_point_in_time, closing_quotes
from ..exits import ExitDesk, exit_decision_id
from ..records import DeskJournal
from ..snapshot import ExecutionSnapshot
from ..status import OpenPosition, open_positions
from .clock import OwnerTimingClock
from .entry_fills import WINDOW
from .mark_snapshots import MarkSnapshots
from .outcomes import EXIT
from .timing_log import TimingLog, TimingRecord

FILLED = "{legs} legs closed at the {mark:%H:%M} mark of {session}"
WAITING = "{legs} without a valid quote at every mark up to {mark:%H:%M} of {session} (retried at the next marks)"


class OwnerTimingExits:
    def __init__(self, clock: OwnerTimingClock, snapshots: MarkSnapshots, desk: ExitDesk, log: TimingLog,
                 view: str, reaction_minutes: int, charges: Mapping[str, float],
                 now: Callable[[], datetime]):  # fmt: skip
        self.clock, self.snapshots, self.desk, self.log = clock, snapshots, desk, log
        self.view, self.reaction, self.charges, self.now = view, reaction_minutes, dict(charges), now

    def apply(self, book: str, position: OpenPosition, alert_time: datetime, journal: DeskJournal) -> str | None:
        """What happened to the exit at the marks that have passed; None while its due mark has not."""
        due = self.clock.due(alert_time, EXIT)
        last_expiry = min(leg.expiry for leg, _ in position.holdings)
        tried = None
        for mark in self.clock.marks_from(due, alert_time, self.now() - WINDOW):
            if mark.date() > last_expiry:
                break  # E7 settles what is left at NSE's final price
            found = self.snapshots.at(mark.date(), mark)
            if found is None or found.prices.finished_at < position.last_fill_at:
                continue  # no copy, or one an earlier run already passed (a later copy closed legs)
            tried = found.prices
            left = self._close_at(book, position, tried, journal, alert_time, due.mark)
            if left is None:
                return self.desk.closed(book, position, tried, journal, "every leg closed").reason
            position = left
        if tried is None:
            return None
        legs = ", ".join(leg.contract for leg, _ in position.holdings)
        waiting = WAITING.format(legs=legs, mark=tried.started_at, session=tried.day)
        return self.desk.pending(book, position, tried, journal, waiting, self.now().date().isoformat()).reason

    def _close_at(self, book: str, position: OpenPosition, snapshot: ExecutionSnapshot, journal: DeskJournal,
                  alert_time: datetime, due_mark: datetime) -> OpenPosition | None:  # fmt: skip
        """Every leg that closes at this copy; the position left open, or None once every leg is closed."""
        check_point_in_time(snapshot, self.now(), not_before=position.last_fill_at)
        closing, pending = closing_quotes(snapshot, position.holdings)
        if closing:  # counted with any leg a stopped run already closed here, so a rerun writes the same record
            earlier = [
                r for r in journal.records.fill_rows(position.trade_id) if r["snapshot_id"] == snapshot.snapshot_id
            ]
            reason = FILLED.format(legs=len(closing) + len(earlier), mark=snapshot.started_at, session=snapshot.day)
            outcome = OUTCOME_PENDING_EXIT if pending else OUTCOME_CLOSED
            self.log.record(
                TimingRecord(
                    book,
                    self.view,
                    position.trade_id,
                    EXIT,
                    self.reaction,
                    alert_time,
                    due_mark,
                    snapshot.started_at,
                    snapshot.snapshot_id,
                    snapshot.sha256,
                    outcome,
                    reason,
                )
            )
            maker = FillMaker(book, position.strategy, exit_decision_id(position.trade_id), position.trade_id,
                              snapshot, self.charges)  # fmt: skip
            for quote in closing:
                journal.record_fill(maker.record(quote, FILL_CLOSE))
        return next((p for p in open_positions(journal.records) if p.trade_id == position.trade_id), None)
