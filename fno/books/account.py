"""A book's paper account (story E1, design 12.6), stored under `journal/<book>/account/`; it opens with
`config.yaml` `risk.paper_account_rs` (story C5):

- `cash_ledger.csv`: append-only, one row per fill, plus the opening balance and any capital top-up (story E1b: dated
  by its write instant, counted as capital only from then). The source of truth.
- `positions.json`: a view rebuilt from the ledger after every write (open legs, cash, closed equity, closed trades).
- `equity_history.csv`: one row per day (cash, closed and marked equity), rewritten for a repeated day; the daily
  run's marking step writes it from the open trades' values (story E2d).

Reading needs no lock (`PaperAccount`). Writing needs the book's held single-writer lock (`AccountWriter`, opened by
`fno.composition.open_account_writer`). Crash safety: a fill is one appended line, flushed to disk before the view is
rebuilt; a restart drops a half-written last line and rebuilds the view, and a fill ID already in the ledger is not
applied again, so a retried run neither loses nor repeats a fill.
"""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path
from typing import Protocol

from ..accounting.ledgers import Trade
from ..constants import CASH_LEDGER_FILE, LEDGER_TOP_UP
from ..models import IST
from .equity import AccountState, Mark, account_state, trade_positions, unmarked_state
from .files import append_durably, complete_lines, csv_text, drop_partial_line, write_atomic
from .fills import CAPITAL_KINDS, FILL_KINDS, LEDGER_COLUMNS, Fill, opening_row, same_fill, top_up_row
from .paths import account_folder, file_in_account

POSITIONS_FILE = "positions.json"
EQUITY_HISTORY_FILE = "equity_history.csv"
EQUITY_COLUMNS = ("date", "cash_rs", "closed_equity_rs", "marked_equity_rs", "open_trades", "stale_marks", "fills")
OPENING_ENTRY_ID = "opening"


@dataclass(frozen=True)
class TopUp:
    amount: float  # rupees added; 0 when the book was already at the target
    further: bool  # a top-up was already recorded before this one (a raised target: an owner decision, lane 1)


def row_instant(filled_at: str) -> datetime:
    """A row's instant; the opening row, dated by day only, counts from the start of its day (IST)."""
    when = datetime.fromisoformat(filled_at)
    return when if when.tzinfo else datetime.combine(when.date(), time.min, IST)


class AccountError(RuntimeError):
    """A write the account refuses: not started, no lock, a fill ID reused for a different fill, a closed trade."""


class WriterLock(Protocol):
    """What a writer needs from the single-writer lock (`fno.books.lock.AccountLock`)."""

    book: str
    path: Path

    @property
    def held(self) -> bool: ...


def _equity_row(day: date, state: AccountState, fills: int) -> dict[str, str]:
    return _row(day, state.cash, state.closed_equity, state.marked_equity, state.open_trades, state.stale_marks, fills)


def _row(day: date, cash: float, closed: float, marked: float, open_trades: int, stale, fills: int) -> dict[str, str]:
    return {
        "date": day.isoformat(),
        "cash_rs": f"{cash:.2f}",
        "closed_equity_rs": f"{closed:.2f}",
        "marked_equity_rs": f"{marked:.2f}",
        "open_trades": str(open_trades),
        "stale_marks": ";".join(stale),
        "fills": str(fills),
    }


class PaperAccount:
    """Read access to one book's account. Every file it touches is inside that book's own account folder."""

    def __init__(self, root: Path, book: str):
        self.book = book
        self.folder = account_folder(root, book)

    def file(self, name: str) -> Path:
        return file_in_account(self.folder, name)

    @property
    def started(self) -> bool:
        return self.file(CASH_LEDGER_FILE).exists()

    def ledger_rows(self) -> list[dict[str, str]]:
        if not self.started:
            return []
        reader = csv.DictReader(io.StringIO(complete_lines(self.file(CASH_LEDGER_FILE).read_text(encoding="utf-8"))))
        if tuple(reader.fieldnames or ()) != LEDGER_COLUMNS:
            raise AccountError(f"{self.book}: cash ledger columns must be {LEDGER_COLUMNS}")
        return list(reader)

    def capital(self, at: datetime | None = None) -> float:
        """The opening plus every top-up written at or before `at` (all when None). Capital is never profit, never a
        trade and never a closed-equity gain (story E1b)."""
        rows = self.ledger_rows()
        if not rows:
            raise AccountError(f"{self.book}: the account has not been started")
        return sum(
            float(row["amount_rs"])
            for row in rows
            if row["kind"] in CAPITAL_KINDS and (at is None or row_instant(row["filled_at"]) <= at)
        )

    def fills(self) -> list[Fill]:
        return [Fill.from_row(row) for row in self.ledger_rows() if row["kind"] in FILL_KINDS]

    def state(
        self, marks: dict[str, Mark], margin_blocked: float = 0.0, premium_reserved: float = 0.0,
        at: datetime | None = None,
    ) -> AccountState:  # fmt: skip
        """`at`: the decision cutoff, so a top-up written after it never counts for that decision (story E1b)."""
        return account_state(self.capital(at), self.fills(), marks, margin_blocked, premium_reserved)

    def summary(self) -> dict:
        """Everything that needs no marks: the content of `positions.json`."""
        rows = self.ledger_rows()
        return {"book": self.book, "ledger_rows": len(rows), "capital_rs": self.capital()} | unmarked_state(
            self.capital(), self.fills()
        )

    def closed_trades(self) -> list[Trade]:
        """Closed trades in the cost accountant's form (C1), for the three ledgers."""
        return [t.as_ledger_trade() for t in trade_positions(self.fills()).values() if not t.is_open]

    def equity_history(self) -> list[dict[str, str]]:
        path = self.file(EQUITY_HISTORY_FILE)
        return list(csv.DictReader(io.StringIO(path.read_text(encoding="utf-8")))) if path.exists() else []


class AccountWriter:
    """The only way to change an account. Each write first checks that this book's lock is held."""

    def __init__(self, account: PaperAccount, lock: WriterLock, opening_cash: float):
        self.account = account
        self._lock = lock
        self.opening_cash = opening_cash  # the owner's paper account size, given by the composition root
        self.require_lock()
        if account.started:
            self._recover()

    def start(self, day: date) -> bool:
        """Open the account with the paper account's cash and no positions. Done once; False (and nothing written) if
        it exists."""
        self.require_lock()
        if self.account.started:
            return False
        opening = opening_row(OPENING_ENTRY_ID, day.isoformat(), self.opening_cash)
        first = _equity_row(day, account_state(self.opening_cash, [], {}), fills=0)
        self._write_atomic(EQUITY_HISTORY_FILE, csv_text(EQUITY_COLUMNS, [first], header=True))
        self._write_atomic(CASH_LEDGER_FILE, csv_text(LEDGER_COLUMNS, [opening], header=True))  # marks "started"
        self._write_positions()
        return True

    def apply_fill(self, fill: Fill) -> bool:
        """Record a fill once. False when this exact fill is already recorded (a retry); an error when its ID was used
        for a different fill or its trade is already closed."""
        self.require_lock()
        rows = self.account.ledger_rows()
        if not rows:
            raise AccountError(f"{self.account.book}: the account has not been started")
        for row in rows:
            if row["entry_id"] == fill.fill_id:
                if same_fill(row, fill):
                    return False
                raise AccountError(f"{self.account.book}: fill ID {fill.fill_id} already records a different fill")
        trade = trade_positions(self.account.fills()).get(fill.trade_id)
        if trade is not None and not trade.is_open:
            raise AccountError(f"{self.account.book}: trade {fill.trade_id} closed on {trade.closed_on}; new ID needed")
        self._append_ledger_row(fill.ledger_row(float(rows[-1]["cash_after_rs"])))
        self._write_positions()
        return True

    def top_up(self, written_at: datetime, target: float) -> TopUp:
        """Story E1b: restore capital (not equity) to `target` with one row at its write instant; nothing written when
        already at `target`. Refused, with nothing written, for a book not started, above `target`, or holding an open
        position (its marked equity would need marks)."""
        self.require_lock()
        rows = self.account.ledger_rows()
        if not rows:
            raise AccountError(f"{self.account.book}: the account has not been started")
        capital = self.account.capital()
        if capital > target:
            raise AccountError(f"{self.account.book}: capital Rs {capital:,.2f} is above Rs {target:,.2f}")
        if any(t.is_open for t in trade_positions(self.account.fills()).values()):
            raise AccountError(f"{self.account.book}: an open position: top up a flat book")
        if capital == target:
            return TopUp(0.0, False)
        further = any(row["kind"] == LEDGER_TOP_UP for row in rows)
        amount = target - capital
        entry_id = f"top_up_{written_at.date().isoformat()}"
        self._append_ledger_row(top_up_row(entry_id, written_at, amount, float(rows[-1]["cash_after_rs"])))
        self._replace_equity_row(_equity_row(written_at.date(), self.account.state({}), len(self.account.fills())))
        self._write_positions()
        return TopUp(amount, further)

    def record_marked_equity(self, day: date, open_trades_value: float, stale: Sequence[str]) -> None:
        """Story E2d: the day's equity row from the open trades' values as S2 gives them (`TradeDay.value`: each
        trade's cash flow so far plus its held legs at their marks), replacing an earlier row for the day. Marked
        equity = closed equity + `open_trades_value` (the identity of `equity.py`); `open_trades_value` is never
        `equity.py`'s `open_value` (the legs alone), which would count the open trades' cash flow twice."""
        self.require_lock()
        summary = self.account.summary()
        closed, opened = summary["closed_equity_rs"], len(summary["open_trades"])
        row = _row(day, summary["cash_rs"], closed, closed + open_trades_value, opened, sorted(set(stale)),
                   len(self.account.fills()))  # fmt: skip
        self._replace_equity_row(row)
        self._write_positions()

    def _replace_equity_row(self, row: dict[str, str]) -> None:
        rows = [r for r in self.account.equity_history() if r["date"] != row["date"]] + [row]
        self._write_atomic(EQUITY_HISTORY_FILE, csv_text(EQUITY_COLUMNS, sorted(rows, key=lambda r: r["date"]), True))

    def require_lock(self) -> None:
        lock = self._lock
        if not (
            lock.held and lock.book == self.account.book and lock.path.parent.resolve() == self.account.folder.resolve()
        ):
            raise AccountError(f"{self.account.book}: writes need this book's single-writer lock, held")

    def _recover(self) -> None:
        """After a crash: drop a half-written last ledger line, then rebuild the view from the ledger."""
        drop_partial_line(self.account.file(CASH_LEDGER_FILE))
        self._write_positions()

    def _append_ledger_row(self, row: dict[str, str]) -> None:
        append_durably(self.account.file(CASH_LEDGER_FILE), csv_text(LEDGER_COLUMNS, [row], header=False))

    def _write_positions(self) -> None:
        self._write_atomic(POSITIONS_FILE, json.dumps(self.account.summary(), indent=1, sort_keys=True) + "\n")

    def _write_atomic(self, name: str, text: str) -> None:
        write_atomic(self.account.file(name), self.account.file(name + ".tmp"), text)
