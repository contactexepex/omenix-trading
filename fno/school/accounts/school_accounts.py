"""The school's `AccountPort` (story MS-P1d): one E1 `PaperAccount` per driver version, opened at the school's
`account_rs` on first use, written only under its single-writer lock (`AccountLock`), mirrored to Drive through E2c's
private files (never committed). E1's ledger keeps cash and units; `PositionBook` keeps what the laws read.

`entries` reads every recorded entry without writing anything (j's settlement runs before the first view).
`view` marks every open position at its road's snapshot and writes the session's equity row once, at the first view
of the session (the slot's marks before its fills), so the daily stop and the brake read fixed rows on any rerun.
Known limit (story 3.6): the loss since the previous slot compares this slot with the previous session's row, so it
includes that slot's own entry costs, which only makes the stop act sooner."""

from collections.abc import Callable, Iterable, Mapping
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Protocol

from ...books.account import AccountError, AccountWriter, PaperAccount
from ...books.equity import trade_positions
from ...books.lock import AccountLock
from ..constants import RoadCode
from ..contracts.accounts import LedgerEntry
from ..contracts.decisions import OpenPosition
from ..contracts.roads import ROADS_BY_CODE
from ..contracts.safety import AccountView
from ..contracts.snapshot import SlotSnapshot
from ..execution.desk_view import signed_units
from .brake import EquityRow, brake_state
from .ledger_fills import ledger_fills
from .names import POSITIONS_FILE, account_files, account_name
from .position_book import PositionBook
from .reviews import BrakeReviews
from .valuation import value_positions


class AccountSync(Protocol):
    """E2c's `PrivateFiles` as the school uses it: each file as Drive holds it, and each written file back."""

    def pull(self, paths: Iterable[Path]) -> None: ...

    def push(self, paths: Iterable[Path]) -> None: ...


class SchoolAccounts:
    def __init__(self, root: Path, account_rs: float, brake_rs: float, charges: Mapping[str, float],
                 reviews: BrakeReviews, sync: AccountSync | None = None,
                 lock: Callable[[Path, str], AccountLock] = AccountLock):  # fmt: skip
        self.root, self.account_rs, self.brake_rs, self.charges = Path(root), account_rs, brake_rs, dict(charges)
        self.reviews, self.sync, self.lock = reviews, sync, lock
        self._pulled: set[str] = set()

    def view(self, driver_id: str, marks: Mapping[RoadCode, SlotSnapshot], session: date) -> AccountView:
        if any(snapshot.session != session for snapshot in marks.values()):
            raise ValueError(f"every mark must be of the session {session}")
        with self._writer(driver_id) as writer:
            account = writer.account
            changed = writer.start(session)
            _not_earlier(driver_id, account, session)
            book = PositionBook(account.file(POSITIONS_FILE))
            open_positions = book.open_positions()
            trades = trade_positions(account.fills())
            _check_consistent(driver_id, open_positions, trades)
            cash_flows = {pid: trade.cash_flow for pid, trade in trades.items()}
            valuation = value_positions(open_positions, cash_flows, marks)
            if not any(row["date"] == session.isoformat() for row in account.equity_history()):
                writer.record_marked_equity(session, valuation.open_value, valuation.unmarked)
                changed = True
            if changed:
                self._push(driver_id)
            summary = account.summary()
            rows = sorted((_row(r) for r in account.equity_history() if r["date"] <= session.isoformat()),
                          key=lambda row: row.session)  # fmt: skip
        equity = summary["closed_equity_rs"] + valuation.open_value
        previous = [row.equity for row in rows if row.session < session]
        brake = brake_state(rows, self.reviews.lifts(driver_id, session), self.brake_rs)
        today = tuple(p for p in book.opened() if p.opened == session)
        return AccountView(driver_id, summary["capital_rs"], summary["cash_rs"], equity, brake.high,
                           max(previous[-1] - equity, 0.0) if previous else 0.0, today, tuple(open_positions),
                           brake.engaged_on, brake.lifted_on)  # fmt: skip

    def record(self, driver_id: str, entry: LedgerEntry) -> None:
        if entry.position.driver_id != driver_id:
            raise ValueError(f"{entry.position.position_id} belongs to {entry.position.driver_id}, not {driver_id}")
        fills = ledger_fills(entry, self.charges)  # checked against the position before anything is written
        with self._writer(driver_id) as writer:
            if not writer.account.started:
                raise AccountError(f"{driver_id}: a fill before the account's first view")
            book = PositionBook(writer.account.file(POSITIONS_FILE))
            book.check(entry)  # an open once per position, a close only of an open one: refused before any fill
            for fill in fills:
                writer.apply_fill(fill)
            book.add(entry)
            self._push(driver_id)

    def entries(self, driver_id: str) -> tuple[LedgerEntry, ...]:
        """Every recorded entry, in the order recorded (j's settlement runs before the session's first `view`, which
        writes the equity row). Read-only: under the lock, pulled once per run, nothing written; an account never
        opened gives (); a ledger that disagrees with the position records raises, never returning half a record."""
        with self._locked(driver_id) as (_, account):
            if not account.started:
                return ()
            book = PositionBook(account.file(POSITIONS_FILE))
            _check_consistent(driver_id, book.open_positions(), trade_positions(account.fills()))
            return tuple(book.entries())

    @contextmanager
    def _locked(self, driver_id: str):
        """The account under its lock, its files pulled from Drive once per run (a failed pull stops, by name)."""
        name = account_name(driver_id)
        with self.lock(self.root, name) as held:
            if self.sync is not None and name not in self._pulled:
                self.sync.pull(account_files(self.root, driver_id))
                self._pulled.add(name)
            yield held, PaperAccount(self.root, name)

    @contextmanager
    def _writer(self, driver_id: str):
        """The account's writer under its lock."""
        with self._locked(driver_id) as (held, account):
            yield AccountWriter(account, held, self.account_rs)

    def _push(self, driver_id: str) -> None:
        """After a write, under the lock: every file back to Drive."""
        if self.sync is not None:
            self.sync.push(account_files(self.root, driver_id))


def _not_earlier(driver_id: str, account: PaperAccount, session: date) -> None:
    """A view never looks back: a session before the account's latest row or fill would value later fills."""
    latest = max([r["date"] for r in account.equity_history()] + [f.filled_at.date().isoformat() for f in
                                                                    account.fills()])  # fmt: skip
    if latest > session.isoformat():
        raise ValueError(f"{driver_id}: the account already holds {latest}; a view of {session} would look ahead")


def _check_consistent(driver_id: str, open_positions: list[OpenPosition], trades) -> None:
    """E1's open trades and the position records must hold the same positions, unit for unit (a crash between the
    two writes, or part way through a close, is repaired by rerunning `record`, which is idempotent; until then
    nothing is valued from half a record)."""
    ledger = {pid: {c: n for c, n in trade.units.items() if n} for pid, trade in trades.items() if trade.is_open}
    held = {p.position_id: signed_units(ROADS_BY_CODE[p.road].underlying, p.legs, p.lot) for p in open_positions}
    if ledger != held:
        raise AccountError(f"{driver_id}: ledger and position records disagree on open positions; rerun the record")


def _row(row: dict[str, str]) -> EquityRow:
    return EquityRow(date.fromisoformat(row["date"]), float(row["marked_equity_rs"]), not row["stale_marks"])
