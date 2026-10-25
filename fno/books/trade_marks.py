"""Story E2d: each open paper trade's value once a session, `journal/<account>/account/trade_marks.csv` (Drive only,
private, with the other account files). One row per open trade and session: its status, its value as S2 gives it (cash
flow so far plus the held legs at their marks), its mark value (the legs alone) and the contracts behind its status.
It is an output only: nothing reads it back to value a trade (the stale fallback comes from the snapshot history)."""

from __future__ import annotations

import csv
import io
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from .account import AccountWriter
from .files import csv_text, write_atomic

TRADE_MARKS_FILE = "trade_marks.csv"
COLUMNS = ("date", "trade_id", "status", "value_rs", "mark_value_rs", "contracts")
VALUED = "valued"
UNMARKED = "unmarked"  # a held leg never had a valid mid: no value, and the book's equity row is not written
AWAITING_SETTLEMENT = "awaiting_settlement"  # a stale leg past its expiry: no quote until NSE's settlement price


@dataclass(frozen=True)
class TradeMark:
    trade_id: str
    status: str
    value: float | None  # S2's `TradeDay.value`; None when unmarked
    mark_value: float | None  # `value` minus the trade's cash flow so far
    contracts: tuple[str, ...] = ()  # the stale contracts, or (unmarked) those never validly quoted

    def row(self, day: date) -> dict[str, str]:
        money = lambda x: "" if x is None else f"{x:.2f}"  # noqa: E731
        return {"date": day.isoformat(), "trade_id": self.trade_id, "status": self.status,
                "value_rs": money(self.value), "mark_value_rs": money(self.mark_value),
                "contracts": ";".join(self.contracts)}  # fmt: skip


def trade_mark_rows(writer: AccountWriter) -> list[dict[str, str]]:
    path = writer.account.file(TRADE_MARKS_FILE)
    return list(csv.DictReader(io.StringIO(path.read_text(encoding="utf-8")))) if path.exists() else []


def write_trade_marks(writer: AccountWriter, day: date, marks: Sequence[TradeMark]) -> None:
    """The session's rows replace any earlier ones of that session (a rerun gives the same bytes); an account that
    never held an open trade at a marking gets no file."""
    writer.require_lock()
    path = writer.account.file(TRADE_MARKS_FILE)
    if not marks and not path.exists():
        return
    rows = [r for r in trade_mark_rows(writer) if r["date"] != day.isoformat()] + [m.row(day) for m in marks]
    text = csv_text(COLUMNS, sorted(rows, key=lambda r: (r["date"], r["trade_id"])), header=True)
    write_atomic(path, writer.account.file(TRADE_MARKS_FILE + ".tmp"), text)
