"""The public per-book daily totals (story E2c): `journal/<book>/daily_totals.csv`, the only part of a paper account
the public repository keeps. One row per date with a ledger row (the opening, a top-up or a fill), as the account stood
at that date's end: closed equity (capital plus the net of closed trades, never an open position's cash or a mark),
the open and closed trade counts and that date's fill count. No contract, price or mark is in it, so no quote can be
rebuilt from it (owner, 15 Oct 2026, "A: move to Drive")."""

from __future__ import annotations

import csv
import io
from datetime import date, datetime, time
from pathlib import Path

from ..constants import DAILY_TOTALS_FILE
from ..models import IST
from .account import PaperAccount, row_instant
from .equity import trade_positions
from .paths import book_folder

COLUMNS = ("date", "closed_equity_rs", "open_trades", "closed_trades", "fills")


def daily_totals(account: PaperAccount) -> list[dict[str, str]]:
    fills = account.fills()
    days = sorted({row_instant(row["filled_at"]).astimezone(IST).date() for row in account.ledger_rows()})
    return [_row(account, fills, day) for day in days]


def write_daily_totals(root: Path, book: str) -> Path:
    """Rewrites the book's file from its account (the same account gives the same bytes); its path."""
    path = book_folder(root, book) / DAILY_TOTALS_FILE
    out = io.StringIO()
    writer = csv.DictWriter(out, COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(daily_totals(PaperAccount(root, book)))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(out.getvalue(), encoding="utf-8")
    return path


def _row(account: PaperAccount, fills: list, day: date) -> dict[str, str]:
    end = datetime.combine(day, time.max, IST)
    trades = trade_positions([f for f in fills if f.filled_at <= end]).values()
    closed = [t for t in trades if not t.is_open]
    closed_equity = account.capital(end) + sum(t.cash_flow for t in closed)
    on_day = sum(1 for f in fills if f.filled_at.astimezone(IST).date() == day)
    open_count = len(trades) - len(closed)
    return {"date": day.isoformat(), "closed_equity_rs": f"{closed_equity:.2f}", "open_trades": str(open_count),
            "closed_trades": str(len(closed)), "fills": str(on_day)}  # fmt: skip
