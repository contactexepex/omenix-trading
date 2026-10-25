"""NSE symbol changes (story P6; judge 42 addendum 3, judge 49): a renamed stock is the same security, so its sessions
under the old symbol are its own history. TATAMOTORS became TMPV on 24 Oct 2025."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import date, datetime

from fno.shared.fo_bhavcopy import BadFile

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
