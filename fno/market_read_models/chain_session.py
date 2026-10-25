"""One session's NIFTY option chain (story P9): the inputs every chain block is cut from, built from the archived NSE
F&O and index files of the history window. The history starts on W13's extract day (1 Jun 2026) and keeps at most
six months, so a daily run reads a bounded number of files (12 Oct 2026: 1 Jun, as W13's examples)."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import date, timedelta

from ..fo_bhavcopy import BadFile, csv_text
from .chain_expiries import ExpiryBuilder, FoRow, in_scope, monthly_expiries, nifty_rows
from .chain_history import chain_history, contract_histories

HISTORY_FIRST_DAY = date(2026, 6, 1)  # W13's extract starts here; no chain history is kept before it
HISTORY_SPAN = timedelta(days=183)
NIFTY_50, INDIA_VIX = "Nifty 50", "India VIX"
CLOSE, CHANGE_PCT = "Closing Index Value", "Change(%)"


def history_start(day: date) -> date:
    return max(HISTORY_FIRST_DAY, day - HISTORY_SPAN)


@dataclass(frozen=True)
class ChainSession:
    """Everything the chain blocks publish for one session."""

    day: date
    underlying: dict  # sym, spot, chg, chg_pct, vix, lot
    expiries: list[dict]  # each expiry's block with its rows
    history: dict  # ChainHistory
    contracts: dict[str, dict]  # code -> ContractHistory
    history_from: date


class ChainBuilder:
    def __init__(self, rate: float):
        self.expiries = ExpiryBuilder(rate)

    def build(
        self, day: date, fo_rows: list[tuple[date, list[dict[str, str]]]], index_files: list[tuple[date, str, bytes]]
    ) -> ChainSession:
        """The session's chain from the window's parsed F&O files ((day, rows)) and index files ((day, name, bytes))."""
        start = history_start(day)
        rows = [r for d, raw in fo_rows if d >= start for r in nifty_rows(d, raw)]
        today = [r for r in rows if r.day == day]
        if not today:
            raise BadFile(f"{day}: no NIFTY contracts in the day's F&O file")
        spot = today[0].underlying
        scope = in_scope(rows, day, spot)
        monthly = monthly_expiries(scope)
        expiries = sorted({r.expiry for r in scope if r.day == day})
        blocks = [self.expiries.block(day, e, _of(scope, day, e), spot, e in monthly) for e in expiries]
        indices = [(d, _nifty_and_vix(data, name)) for d, name, data in index_files if start <= d <= day]
        dates = [d for d, _ in indices]
        nifty, vix = [x[NIFTY_50][0] for _, x in indices], [x[INDIA_VIX][0] for _, x in indices]
        underlying = {
            "sym": "NIFTY", "spot": spot, "chg": round(spot - nifty[-2], 2), "chg_pct": indices[-1][1][NIFTY_50][1],
            "vix": vix[-1], "lot": today[0].lot,
        }  # fmt: skip
        history = chain_history(dates, nifty, vix, scope, expiries)
        return ChainSession(day, underlying, blocks, history, contract_histories(scope, monthly), dates[0])


def _of(rows: list[FoRow], day: date, expiry: date) -> list[FoRow]:
    return [r for r in rows if r.day == day and r.expiry == expiry]


def _nifty_and_vix(data: bytes, filename: str) -> dict[str, tuple[float, float | None]]:
    """NIFTY 50 and India VIX: (close, the day's change in percent) from NSE's daily index file."""
    found = {}
    for row in csv.DictReader(io.StringIO(csv_text(filename, data))):
        name = (row.get("Index Name") or "").strip()
        if name in (NIFTY_50, INDIA_VIX):
            change = (row.get(CHANGE_PCT) or "").strip()
            found[name] = (float(row[CLOSE]), float(change) if change not in ("", "-") else None)
    if len(found) < 2:
        raise BadFile(f"{filename}: needs {NIFTY_50} and {INDIA_VIX}")
    return found
