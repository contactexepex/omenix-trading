"""NSE symbol changes (story P6; judge 42 addendum 3, judge 49): a renamed stock is the same security, so its sessions
under the old symbol are its own history. TATAMOTORS became TMPV on 24 Oct 2025; its demerger (ex-date 14 Oct 2025,
listed by NSE under TMPV) traded as TATAMOTORS, so without the join the year has 239 sessions and no ex-date trade."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, replace
from datetime import date, datetime

from ..fo_bhavcopy import BadFile
from .corporate_actions import CorporateAction
from .nse_files import EquityBar

COLUMNS = ("OLD SYMBOL", "NEW SYMBOL", "EFFECTIVE DATE")
EFFECTIVE_FORMAT = "%d-%b-%Y"


@dataclass(frozen=True)
class SymbolChange:
    old: str
    new: str
    effective: date  # the first session under the new symbol


def read_symbol_changes(data: bytes, filename: str) -> list[SymbolChange]:
    """Every change in NSE's symbolchange.csv (its header names have padding; rows without a date are skipped)."""
    reader = csv.reader(io.StringIO(data.decode("utf-8-sig", errors="replace")))
    header = [name.strip().upper() for name in next(reader, [])]
    if not all(column in header for column in COLUMNS):
        raise BadFile(f"{filename}: needs the columns {', '.join(COLUMNS)}")
    old, new, effective = (header.index(column) for column in COLUMNS)
    changes = []
    for row in reader:
        if len(row) > max(old, new, effective) and row[effective].strip():
            day = datetime.strptime(row[effective].strip(), EFFECTIVE_FORMAT).date()
            changes.append(SymbolChange(row[old].strip(), row[new].strip(), day))
    return changes


def joined(
    series: dict[str, list[EquityBar]], actions: list[CorporateAction], changes: list[SymbolChange]
) -> tuple[dict[str, list[EquityBar]], list[CorporateAction]]:
    """Each renamed stock's sessions under its old symbol put before its new symbol's, and its actions listed under
    the old symbol moved to the new one; in effective-date order, so a chain of renames joins up."""
    series, actions = dict(series), list(actions)
    for change in sorted(changes, key=lambda c: c.effective):
        earlier = [b for b in series.get(change.old, []) if b.day < change.effective]
        if not earlier or change.new not in series:
            continue
        series[change.new] = [replace(b, symbol=change.new) for b in earlier] + series[change.new]
        del series[change.old]
        actions = [replace(a, symbol=change.new) if a.symbol == change.old else a for a in actions]
    return series, actions
