"""Expiry settlement before the session's first view (story MS-P1j; judge 486's note): a position whose expiry passed
has no mark in the session's capture, so a view taken before its settlement would count it at minus its maximum loss
and could trip the daily stop. Each expired position, in every driver's account and in the ticket ledger, closes at
intrinsic against NSE's archived settlement file; until that file exists it stays `settlement_needed`.

Each settlement is an `ExitRecord` (reason `expiry`) sealed with the session's decisions; its outcome is rebuilt
from the ledgers when the outcomes are sealed (`outcomes.outcomes_of`). The exit records themselves are rebuilt from the
ledgers too: every expiry closing recorded for this session (`LedgerEntry.recorded_for`), so a crash after a settlement
is recorded and before the decisions' seal still seals its exit record and its outcome on the rerun (orchestrator's
ruling b, 22 Oct 2026)."""

from collections.abc import Iterable
from datetime import date

from ..constants import SLOT_1500, ExitReason
from ..contracts.accounts import LedgerEntry
from ..contracts.decisions import OpenPosition
from ..contracts.records import ExitRecord
from .books import Books, account_call
from .ledgers import open_positions
from .outcomes import TICKET_PREFIX


def expiry_of(position: OpenPosition) -> date:
    return min(leg.key.expiry for leg in position.legs)


def is_ticket_id(position_id: str) -> bool:
    return position_id.startswith(TICKET_PREFIX)


def settle_expired(books: Books, driver_ids: Iterable[str], session: date) -> tuple[ExitRecord, ...]:
    """Settles every expired open position it can, then returns the exit records of every settlement recorded for
    this session, this run's and a crashed earlier run's alike."""
    ids = tuple(driver_ids)
    for driver_id in ids:
        for reader in (books.account_entries, books.ticket_entries):
            for position in open_positions(account_call(driver_id, reader.entries, driver_id)):
                if expiry_of(position) < session:
                    account_call(driver_id, _settle, books, position, session)
    return settlements_of(books, ids, session)


def _settle(books: Books, position: OpenPosition, session: date) -> None:
    if is_ticket_id(position.position_id):
        books.tickets.settle(position, expiry_of(position), session)
        return
    fill = books.fills.settle(position, expiry_of(position))
    if fill.filled:
        closing = LedgerEntry(position, fill, closes=True, exit_reason=ExitReason.EXPIRY, recorded_for=session)
        books.accounts.record(position.driver_id, closing)


def settlements_of(books: Books, driver_ids: Iterable[str], session: date) -> tuple[ExitRecord, ...]:
    return tuple(ExitRecord(session, SLOT_1500, e.position.position_id, driver_id, e.position.road, ExitReason.EXPIRY,
                            "")
                 for driver_id in driver_ids for reader in (books.account_entries, books.ticket_entries)
                 for e in account_call(driver_id, reader.entries, driver_id)
                 if e.closes and e.exit_reason == ExitReason.EXPIRY and e.recorded_for == session)  # fmt: skip
