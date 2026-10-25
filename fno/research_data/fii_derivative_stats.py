"""Reads NSE's daily FII derivatives statistics file (story A23; Excel 97, read with xlrd): FII buy, sell and
end-of-day open interest, in contracts and crores, for the four groups every year has (index and stock futures and
options) and, where the file has them (2026), one row per index future and option.

Checked before anything is returned (a damaged file is never read partly): the title's date must be the file's day,
the four groups must be there, any other row before the notes must be an index's FUTURES or OPTIONS row, every cell a
number (contracts whole), and where per-index rows exist their contracts must add up to their group's (within NSE's
own rounding, `SUM_TOLERANCE`)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime

import xlrd

from ..fo_bhavcopy import BadFile

GROUPS = ("INDEX FUTURES", "INDEX OPTIONS", "STOCK FUTURES", "STOCK OPTIONS")
INDEX_ROW = re.compile(r"^[A-Z0-9]+ (FUTURES|OPTIONS)$")  # "BANKNIFTY FUTURES", "NIFTYNXT50 OPTIONS"
TITLE = re.compile(r"^FII DERIVATIVES STATISTICS FOR (\d{2}-[A-Za-z]{3}-\d{4})$")
NOTES = "Notes:"
SUM_TOLERANCE = 2  # contracts: NSE's own sums are up to 2 off their parts (A8 measured it; 12 Jan 2026 here: 1)
VALUES_PER_ROW = 6  # buy contracts, buy crores, sell contracts, sell crores, OI contracts, OI crores


@dataclass(frozen=True)
class FiiFlow:
    buy_contracts: int
    buy_crores: float
    sell_contracts: int
    sell_crores: float
    oi_contracts: int
    oi_crores: float

    @property
    def net_crores(self) -> float:
        return self.buy_crores - self.sell_crores

    @property
    def net_contracts(self) -> int:
        return self.buy_contracts - self.sell_contracts


@dataclass(frozen=True)
class FiiDerivativeStats:
    day: date
    groups: dict[str, FiiFlow]  # the four groups, every year
    indices: dict[str, FiiFlow]  # "NIFTY FUTURES" ... where the file has them, else empty


def read_fii_derivative_stats(data: bytes, filename: str, day: date) -> FiiDerivativeStats:
    return parse_fii_rows(_rows(data, filename), filename, day)


def parse_fii_rows(rows: list[list], filename: str, day: date) -> FiiDerivativeStats:
    """The sheet's rows as xlrd gives them (numbers as floats, or as text in 2026's files)."""
    _check_title(rows[0][0] if rows and rows[0] else "", filename, day)
    flows = {}
    for row in rows[1:]:
        label = str(row[0]).strip() if row else ""
        if label == NOTES:
            break
        if label and label not in GROUPS and not INDEX_ROW.match(label):
            raise BadFile(f"{filename}: unknown row {label!r}")
        if label:
            flows[label] = _flow(row, label, filename)
    missing = [group for group in GROUPS if group not in flows]
    if missing:
        raise BadFile(f"{filename}: no row for {missing}")
    indices = {label: flow for label, flow in flows.items() if label not in GROUPS}
    _check_index_sums(indices, flows, filename)
    return FiiDerivativeStats(day, {group: flows[group] for group in GROUPS}, indices)


def _rows(data: bytes, filename: str) -> list[list]:
    if not data:  # xlrd reads empty contents as "no contents given" and looks for a file path instead
        raise BadFile(f"{filename}: not an Excel 97 workbook (empty)")
    try:
        sheet = xlrd.open_workbook(file_contents=data).sheet_by_index(0)
    except (xlrd.XLRDError, ValueError, IndexError, AssertionError) as exc:  # xlrd's errors for a damaged file
        raise BadFile(f"{filename}: not an Excel 97 workbook ({type(exc).__name__})") from exc
    return [sheet.row_values(n) for n in range(sheet.nrows)]


def _check_title(title, filename: str, day: date) -> None:
    found = TITLE.match(str(title).strip())
    if not found:
        raise BadFile(f"{filename}: no 'FII DERIVATIVES STATISTICS FOR <date>' title")
    if datetime.strptime(found.group(1), "%d-%b-%Y").date() != day:
        raise BadFile(f"{filename}: the title says {found.group(1)}, the file is for {day}")


def _flow(row: list, label: str, filename: str) -> FiiFlow:
    cells = row[1 : 1 + VALUES_PER_ROW]
    try:
        numbers = [float(str(cell).replace(",", "").strip()) for cell in cells]
    except ValueError as exc:
        raise BadFile(f"{filename}: row {label!r} has a value that is not a number") from exc
    if len(numbers) != VALUES_PER_ROW or any(numbers[n] != int(numbers[n]) for n in (0, 2, 4)):
        raise BadFile(f"{filename}: row {label!r} needs {VALUES_PER_ROW} numbers, contracts whole")
    return FiiFlow(int(numbers[0]), numbers[1], int(numbers[2]), numbers[3], int(numbers[4]), numbers[5])


def _check_index_sums(indices: dict[str, FiiFlow], flows: dict[str, FiiFlow], filename: str) -> None:
    for kind in ("FUTURES", "OPTIONS"):
        rows = [flow for label, flow in indices.items() if label.endswith(kind)]
        if not rows:
            continue
        total = flows[f"INDEX {kind}"]
        for field in ("buy_contracts", "sell_contracts", "oi_contracts"):
            added, stated = sum(getattr(flow, field) for flow in rows), getattr(total, field)
            if abs(added - stated) > SUM_TOLERANCE:
                raise BadFile(f"{filename}: index {kind.lower()} {field} add up to {added}, not {stated}")
