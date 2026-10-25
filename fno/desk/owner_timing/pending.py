"""What waits for an owner-timing fill (story E8 rule 11), read from the verdict account's own desk records, never kept
as separate state: an entry the daily run handed over (`entry_pending`) until its entry outcome is recorded, and an
open position whose exit is ordered until it is closed. Each entry's order is the one kept at its hand-over
(`order_record.py`), never rebuilt."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date

from ...constants import OUTCOME_ENTRY_PENDING
from ..entries import EntryOrder
from ..records import DeskRecords
from ..status import ENTRY_OUTCOMES, OpenPosition, open_positions


class OrderMissing(LookupError):
    """A handed-over entry without its kept order: the step fails, never guesses (entries fail closed)."""


@dataclass(frozen=True)
class PendingEntry:
    book: str
    trade_id: str
    day: date  # the decision day: its card carries the trade


def pending_entries(book: str, records: DeskRecords) -> list[PendingEntry]:
    events = records.event_rows()
    done = {e["trade_id"] for e in events if e["outcome"] in ENTRY_OUTCOMES}
    waiting = [e for e in events if e["outcome"] == OUTCOME_ENTRY_PENDING and e["trade_id"] not in done]
    return [PendingEntry(book, e["trade_id"], date.fromisoformat(e["day"])) for e in waiting]


def pending_exits(records: DeskRecords) -> list[OpenPosition]:
    return [p for p in open_positions(records) if p.exit_reason]


class OrderSource(ABC):
    @abstractmethod
    def order(self, pending: PendingEntry) -> EntryOrder:
        """The handed-over entry's order as kept at its hand-over; `OrderMissing` when none was kept."""
