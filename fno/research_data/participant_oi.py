"""Reads NSE's daily participant-wise open interest file (story A8): for each participant (client, DII, FII, pro), the
long and short contracts it holds in each instrument group at the day's close.

The file is checked before anything is returned (a damaged file is never read partly): the date in its title must be
the file's day, the columns and participants must be NSE's, and the exchange's own identities must hold (each
participant's groups add up to its totals, the participants add up to the TOTAL row, and every contract has a long and
a short side), within NSE's own rounding (`ROUNDING_TOLERANCE`). NSE's header spacing, quoting and month names vary
over the years; the numbers are returned exactly as written.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import date

from ..constants import (
    MONTH_CODES,
    OI_FUTURE_INDEX,
    OI_FUTURE_STOCK,
    OI_GROUPS,
    OI_OPTION_INDEX_CALL,
    OI_OPTION_INDEX_PUT,
    OI_OPTION_STOCK_CALL,
    OI_OPTION_STOCK_PUT,
    PARTICIPANTS,
)
from ..fo_bhavcopy import BadFile

LONG, SHORT = "long", "short"
TOTAL_ROW = "TOTAL"
ROUNDING_TOLERANCE = (
    2  # contracts: NSE's sums can be up to 2 off their parts (rounding): measured, 1,929 files 2019-2026
)
GROUP_COLUMNS = {  # NSE's column for each instrument group and side, in the file's order
    (OI_FUTURE_INDEX, LONG): "Future Index Long",
    (OI_FUTURE_INDEX, SHORT): "Future Index Short",
    (OI_FUTURE_STOCK, LONG): "Future Stock Long",
    (OI_FUTURE_STOCK, SHORT): "Future Stock Short",
    (OI_OPTION_INDEX_CALL, LONG): "Option Index Call Long",
    (OI_OPTION_INDEX_PUT, LONG): "Option Index Put Long",
    (OI_OPTION_INDEX_CALL, SHORT): "Option Index Call Short",
    (OI_OPTION_INDEX_PUT, SHORT): "Option Index Put Short",
    (OI_OPTION_STOCK_CALL, LONG): "Option Stock Call Long",
    (OI_OPTION_STOCK_PUT, LONG): "Option Stock Put Long",
    (OI_OPTION_STOCK_CALL, SHORT): "Option Stock Call Short",
    (OI_OPTION_STOCK_PUT, SHORT): "Option Stock Put Short",
}
TOTAL_COLUMNS = {LONG: "Total Long Contracts", SHORT: "Total Short Contracts"}
COLUMNS = ("Client Type", *GROUP_COLUMNS.values(), *TOTAL_COLUMNS.values())
TITLE_DATE = re.compile(r"as on\W*([A-Za-z]{3})[a-z]*\W*(\d{1,2})(?:\W+(\d{4}))?")  # typed by hand: "Aug 05 2019"


@dataclass(frozen=True)
class Position:
    long: int
    short: int

    @property
    def net(self) -> int:
        return self.long - self.short


@dataclass(frozen=True)
class ParticipantOi:
    day: date
    positions: dict[str, dict[str, Position]]  # participant -> instrument group -> contracts
    totals: dict[str, Position]  # participant -> all groups together

    def position(self, participant: str, group: str) -> Position:
        return self.positions[participant][group]


def _check_title(title: str, filename: str, day: date) -> None:
    """The title's date must be the file's day; a title without a year (8 Jun 2021) must match month and day."""
    found = TITLE_DATE.search(title)
    if not found or found.group(1).upper() not in MONTH_CODES:
        raise BadFile(f"{filename}: no 'as on <date>' in the title {title!r}")
    month, number, year = MONTH_CODES.index(found.group(1).upper()) + 1, int(found.group(2)), found.group(3)
    if (month, number) != (day.month, day.day) or (year is not None and int(year) != day.year):
        raise BadFile(f"{filename}: the title says {found.group(0)!r}, the file is for {day}")


def _rows(data: bytes, filename: str) -> tuple[str, dict[str, list[str]]]:
    """The title line as written (its quoting varies) and each participant's cells under NSE's named columns. Columns
    without a header name are ignored whatever they hold (22 Feb 2024: one stray sum in the FII row)."""
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise BadFile(f"{filename}: not a text file") from exc
    text_lines = [line for line in text.splitlines() if line.strip(", \t")]
    lines = list(csv.reader(text_lines))
    if len(lines) < 2:
        raise BadFile(f"{filename}: no title and header")
    header = [cell.strip() for cell in lines[1]]
    if tuple(header[: len(COLUMNS)]) != COLUMNS or any(header[len(COLUMNS) :]):
        raise BadFile(f"{filename}: unexpected columns {header}")
    body = {row[0].strip(): row for row in lines[2:]}
    if len(body) != len(lines) - 2 or set(body) != {*PARTICIPANTS, TOTAL_ROW}:
        raise BadFile(f"{filename}: participants {sorted(body)} are not {sorted({*PARTICIPANTS, TOTAL_ROW})}")
    for name, row in body.items():
        if not len(COLUMNS) <= len(row) <= len(header):
            raise BadFile(f"{filename}: row {name!r} has {len(row)} values, not {len(COLUMNS)}")
    return text_lines[0], {name: row[: len(COLUMNS)] for name, row in body.items()}


def _count(cell: str) -> int:
    """A whole number of contracts, also as NSE sometimes wrote one: "10,02,064.00" (Indian grouping, zero fraction)."""
    whole, _, fraction = cell.strip().replace(",", "").partition(".")
    if not whole.isdigit() or fraction.strip("0"):
        raise ValueError(cell)
    return int(whole)


def _numbers(row: list[str], filename: str) -> dict[str, int]:
    try:
        return {name: _count(cell) for name, cell in zip(COLUMNS[1:], row[1:])}
    except ValueError as exc:
        raise BadFile(f"{filename}: row {row[0].strip()!r} has a value that is not a whole number") from exc


def _check_identities(numbers: dict[str, dict[str, int]], filename: str) -> None:
    for name, values in numbers.items():
        for side in (LONG, SHORT):
            groups = sum(values[GROUP_COLUMNS[group, side]] for group in OI_GROUPS)
            if abs(groups - values[TOTAL_COLUMNS[side]]) > ROUNDING_TOLERANCE:
                raise BadFile(f"{filename}: {name} {side} groups add up to {groups}, not {values[TOTAL_COLUMNS[side]]}")
    for column in COLUMNS[1:]:
        added = sum(numbers[name][column] for name in PARTICIPANTS)
        if abs(added - numbers[TOTAL_ROW][column]) > ROUNDING_TOLERANCE:
            raise BadFile(f"{filename}: participants' {column} add up to {added}, not {numbers[TOTAL_ROW][column]}")
    for group in OI_GROUPS:
        if abs(_position(numbers[TOTAL_ROW], group).net) > ROUNDING_TOLERANCE:
            raise BadFile(f"{filename}: total {group} long and short contracts differ")


def _position(values: dict[str, int], group: str) -> Position:
    return Position(values[GROUP_COLUMNS[group, LONG]], values[GROUP_COLUMNS[group, SHORT]])


def read_participant_oi(data: bytes, filename: str, day: date) -> ParticipantOi:
    """The positions in session `day`'s file; BadFile when it is damaged, not NSE's format, or for another day."""
    title, body = _rows(data, filename)
    _check_title(title, filename, day)
    numbers = {name: _numbers(row, filename) for name, row in body.items()}
    _check_identities(numbers, filename)
    positions = {name: {group: _position(numbers[name], group) for group in OI_GROUPS} for name in PARTICIPANTS}
    totals = {
        name: Position(numbers[name][TOTAL_COLUMNS[LONG]], numbers[name][TOTAL_COLUMNS[SHORT]]) for name in PARTICIPANTS
    }
    return ParticipantOi(day, positions, totals)
