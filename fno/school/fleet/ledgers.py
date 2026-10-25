"""What the fleet derives from the ledgers' recorded entries (a3's `LedgerReader`, read-only): open positions, so
settlement runs before the session's first `view` (judge 486's note: a view writes the session's equity row), and
the fills already recorded, so a rerun after a crash records nothing twice and serves the shared size exactly as one
clean run would (MS-P1j: the finish is rebuilt from the sealed records and the ledgers on every run)."""

from collections.abc import Iterable
from dataclasses import dataclass

from ..constants import Outcome
from ..contracts.accounts import FillResult, LedgerEntry, SealedDecision
from ..contracts.decisions import OpenPosition
from ..contracts.records import DecisionRecord
from ..tickets.book import ticket_id
from .books import Books, account_call
from .running_view import position_id


def open_positions(entries: tuple[LedgerEntry, ...]) -> tuple[OpenPosition, ...]:
    closed = {e.position.position_id for e in entries if e.closes}
    return tuple(e.position for e in entries if not e.closes and e.position.position_id not in closed)


def ledger_id(record: DecisionRecord) -> str:
    """The position a sealed trade or ticket opens: `ticket:` IDs in the ticket ledger, plain IDs in the account."""
    if record.decision.outcome == Outcome.TICKET:
        return ticket_id(SealedDecision(record.decision, ""))
    return position_id(record.decision)


@dataclass(frozen=True)
class Recorded:
    """Every driver's two ledgers as they stand, by position ID: each opening's and closing's fill, and what is open."""

    openings: dict[str, FillResult]
    closings: dict[str, FillResult]
    still_open: dict[str, OpenPosition]


def recorded(books: Books, driver_ids: Iterable[str]) -> Recorded:
    openings, closings, still_open = {}, {}, {}
    for driver_id in driver_ids:
        for reader in (books.account_entries, books.ticket_entries):
            entries = account_call(driver_id, reader.entries, driver_id)
            for entry in entries:
                (closings if entry.closes else openings)[entry.position.position_id] = entry.fill
            still_open |= {p.position_id: p for p in open_positions(entries)}
    return Recorded(openings, closings, still_open)
