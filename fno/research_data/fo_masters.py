"""Readers of the daily F&O master files NSE replaces in place (story A20a): the ban list and the market lots. Each
raises BadFile (a ValueError) for a file that is damaged or not in its layout, so the archive's content check and any
later reader use the same function; nothing is ever read partly."""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from datetime import date, datetime

from ..fo_bhavcopy import BadFile

BAN_HEADER = re.compile(r"^Securities in Ban For Trade Date (\d{2}-[A-Z]{3}-\d{4}):$")
BAN_ROW = re.compile(r"^(\d+),([A-Z0-9&-]+)$")
LOT_KEY_COLUMNS = ("UNDERLYING", "SYMBOL")
LOT_SECTION_SYMBOL = "Symbol"  # the row that opens NSE's stock section repeats the header in title case
LOT_REQUIRED_SYMBOL = "NIFTY"


@dataclass(frozen=True)
class BanList:
    trade_date: date
    symbols: tuple[str, ...]


def read_ban_list(data: bytes, filename: str) -> BanList:
    """The trade date the list is for and its securities, in NSE's order (an empty list is valid)."""
    lines = data.decode("utf-8-sig").strip().splitlines()
    header = BAN_HEADER.match(lines[0].strip()) if lines else None
    if header is None:
        raise BadFile(f"{filename}: no 'Securities in Ban For Trade Date' line")
    rows = [BAN_ROW.match(line.strip()) for line in lines[1:]]
    if not all(rows):
        raise BadFile(f"{filename}: a line is not '<number>,<symbol>'")
    numbers = [int(r.group(1)) for r in rows]
    if numbers != list(range(1, len(rows) + 1)):
        raise BadFile(f"{filename}: rows are not numbered 1..{len(rows)}")
    trade_date = datetime.strptime(header.group(1).title(), "%d-%b-%Y").date()
    return BanList(trade_date, tuple(r.group(2) for r in rows))


def ban_list_trade_date(filename: str, data: bytes) -> date:
    """The session a ban list is for: where the archive files it."""
    return read_ban_list(data, filename).trade_date


def read_lot_sizes(data: bytes, filename: str) -> dict[str, dict[str, int]]:
    """Symbol -> {expiry month as NSE writes it (e.g. 'OCT-26'): lot}, blank cells left out."""
    rows = [[cell.strip() for cell in row] for row in csv.reader(io.StringIO(data.decode("utf-8-sig"))) if row]
    if not rows or tuple(rows[0][:2]) != LOT_KEY_COLUMNS or len(rows[0]) < 3:
        raise BadFile(f"{filename}: needs the columns {LOT_KEY_COLUMNS} and at least one expiry month")
    months = rows[0][2:]
    lots = {}
    for row in rows[1:]:
        if len(row) != len(rows[0]):
            raise BadFile(f"{filename}: a row has {len(row)} cells, the header {len(rows[0])}")
        if row[1] == LOT_SECTION_SYMBOL:
            continue
        try:
            lots[row[1]] = {month: int(cell) for month, cell in zip(months, row[2:]) if cell}
        except ValueError as exc:
            raise BadFile(f"{filename}: {row[1]}: {exc}") from exc
    if LOT_REQUIRED_SYMBOL not in lots:
        raise BadFile(f"{filename}: no {LOT_REQUIRED_SYMBOL} row")
    return lots
