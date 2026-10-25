"""The daily run's `owner_timing_fills` step (story E8 rule 11), right after the quote parts start and before every
other step, so that C2 sees this morning's fills before today's decision.

1. It seals the availability file's current version (rule 8), before that day's card.
2. It applies every pending entry and exit of the verdict accounts whose due mark has passed, oldest order time first,
   catching up after a missed run; each item's writes land before the next item's checks read the account (judge 203
   condition 4). An entry whose card was never delivered has no order time and is missed first.
3. A refused availability file (a changed sealed line, a shallow clone), a read past its cap or the step's deadline, an
   order that cannot be rebuilt or a copy that fails its checks ends the step: refused or failed, with its reason. The
   daily run then opens no new entry in any book today, while every exit still runs (rule 11)."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import UTC, date, datetime
from pathlib import Path

from ...constants import STEP_FAILED, STEP_NOT_LIVE, STEP_OK, STEP_REFUSED
from ..daily_ports import DayStep
from ..daily_steps import StepOutcome
from ..records import DeskJournal, DeskRecords
from ..snapshot import SnapshotError
from .account_writes import StepAccountWrites
from .availability import AvailabilityRefused, AvailabilitySealer
from .entry_fills import OwnerTimingEntries
from .exit_fills import OwnerTimingExits
from .order_times import CardTimes
from .pending import OrderMissing, OrderSource, PendingEntry, pending_entries, pending_exits
from .timed_reads import StepDeadline, StepTimedOut
from .timing_log import TimingLog

APPLIED = "{done} applied, {waiting} waiting for their due mark"
EARLIEST = datetime.min.replace(tzinfo=UTC)  # an entry without an order time is decided (missed) first
FAILURES = (StepTimedOut, OrderMissing, SnapshotError)
SEALED_ONLY = "not live yet: availability sealed, no fills"
SEAL_FAILED = "not live; sealing failed: {problem} (blocks nothing until the live date)"


class OwnerTimingStep(DayStep):
    def __init__(self, books: Sequence[str], sealer: AvailabilitySealer, seal_file: Path, sync: StepAccountWrites,
                 records: Callable[[str], DeskRecords], orders: OrderSource, cards: CardTimes, alerts: TimingLog,
                 entries: OwnerTimingEntries, exits: OwnerTimingExits, deadline: StepDeadline,
                 clock: Callable[[], datetime]):  # fmt: skip
        self.books, self.sealer, self.seal_file, self.sync, self.records = books, sealer, seal_file, sync, records
        self.orders, self.cards, self.alerts, self.entries, self.exits = orders, cards, alerts, entries, exits
        self.deadline, self.clock = deadline, clock

    def run(self, day: date) -> StepOutcome:
        self.deadline.restart()
        sealed = None
        try:
            sealed = self.sealer.seal(self.clock())
            results = [self._apply(item) for _, item in sorted(self._pending(), key=lambda pair: pair[0])]
        except AvailabilityRefused as refused:
            return self._outcome(sealed, {"status": STEP_REFUSED, "reason": str(refused)})
        except FAILURES as failure:
            return self._outcome(sealed, {"status": STEP_FAILED, "reason": f"{type(failure).__name__}: {failure}"})
        done = [r for r in results if r["outcome"] is not None]
        reason = APPLIED.format(done=len(done), waiting=len(results) - len(done))
        return self._outcome(sealed, {"status": STEP_OK, "reason": reason, "items": results})

    def seal_only(self, day: date) -> StepOutcome:
        """Before E8's live date (judge 203 early view 5): only the availability seal, so its history exists at
        go-live. Nothing is pending then; a failed seal blocks nothing, and is marked so the switch alerts it."""
        self.deadline.restart()
        try:
            sealed = self.sealer.seal(self.clock())
        except Exception as problem:  # noqa: BLE001 - before go-live nothing may block entries (Drive down included)
            failed = {"status": STEP_NOT_LIVE, "reason": SEAL_FAILED.format(problem=problem), "seal_failed": True}
            return self._outcome(None, failed)
        return self._outcome(sealed, {"status": STEP_NOT_LIVE, "reason": SEALED_ONLY})

    def _outcome(self, sealed, result: dict) -> StepOutcome:
        """What was written before any failure is committed with the step's entry: the new seal, the totals."""
        paths = ((self.seal_file,) if sealed else ()) + self.sync.paths()
        return StepOutcome({"sealed": sealed is not None}, result, paths)

    def _pending(self) -> list[tuple[datetime, tuple]]:
        """Every waiting entry and exit of every verdict account, each with its order time (the sort key)."""
        found = []
        for book in self.books:
            records = self.records(book)
            for entry in pending_entries(book, records):
                delivered = self.cards.delivered(entry.day)
                found.append((delivered or EARLIEST, ("entry", entry, delivered)))
            for position in pending_exits(records):
                alerted = self.alerts.alert_time(book, position.trade_id)
                if alerted is not None:  # an undelivered alert is sent again by the exit review: no T yet
                    found.append((alerted, ("exit", (book, position.trade_id), alerted)))
        return found

    def _apply(self, item: tuple) -> dict:
        kind, what, order_time = item
        if kind == "entry":
            return self._entry(what, order_time)
        book, trade_id = what
        message = f"owner-timing exit {book} {trade_id}"
        outcome = self.sync.write(book, lambda journal: self._exit(book, trade_id, order_time, journal), message)
        return {"kind": kind, "book": book, "trade_id": trade_id, "outcome": outcome}

    def _entry(self, pending: PendingEntry, card_time: datetime | None) -> dict:
        order = self.orders.order(pending)
        message = f"owner-timing entry {pending.book} {pending.trade_id}"
        outcome = self.sync.write(pending.book, lambda journal: self.entries.apply(order, card_time, journal), message)
        return {"kind": "entry", "book": pending.book, "trade_id": pending.trade_id, "outcome": outcome}

    def _exit(self, book: str, trade_id: str, alert_time: datetime, journal: DeskJournal) -> str | None:
        position = next((p for p in pending_exits(journal.records) if p.trade_id == trade_id), None)
        return None if position is None else self.exits.apply(book, position, alert_time, journal)
