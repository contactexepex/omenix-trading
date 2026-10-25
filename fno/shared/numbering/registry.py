"""A category's registry rows (story O12): `number,name,session,claimed_at_utc`, one row per claimed number.

Rows with session `existing` were seeded from the files already on `main` (no time); every later row is a claim.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from fno.shared.numbering.categories import AddendumCategory, Category

HEADER = ("number", "name", "session", "claimed_at_utc")
SEEDED = "existing"
UTC_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
STAMP_SHAPE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")


@dataclass(frozen=True)
class Row:
    number: str
    name: str
    session: str
    claimed_at_utc: str = ""

    @property
    def seeded(self) -> bool:
        return self.session == SEEDED

    def as_line(self) -> str:
        out = io.StringIO()
        csv.writer(out, lineterminator="\n").writerow((self.number, self.name, self.session, self.claimed_at_utc))
        return out.getvalue()


def utc_stamp(moment: datetime) -> str:
    return moment.strftime(UTC_FORMAT)


def valid_stamp(text: str) -> bool:
    if not STAMP_SHAPE.fullmatch(text):  # strptime alone takes "2026-1-5T1:2:3Z"
        return False
    try:
        datetime.strptime(text, UTC_FORMAT)
    except ValueError:
        return False
    return True


def read_rows(path: Path) -> list[Row]:
    """The registry's rows; a missing file is an empty registry. A row with the wrong column count raises ValueError.
    Blank lines and a byte-order mark (a hand edit on another system) are tolerated."""
    return rows_from_text(path.read_text(encoding="utf-8-sig")) if path.exists() else []


def rows_from_text(text: str) -> list[Row]:
    """`read_rows` on a registry's text (a committed copy, story O12e)."""
    lines = [cells for cells in csv.reader(io.StringIO(text.removeprefix("\ufeff"))) if cells]
    if not lines or tuple(lines[0]) != HEADER:
        raise ValueError(f"the first line must be {','.join(HEADER)}")
    rows = []
    for at, cells in enumerate(lines[1:], start=2):
        if len(cells) != len(HEADER):
            raise ValueError(f"line {at}: {len(cells)} columns, expected {len(HEADER)}")
        rows.append(Row(*cells))
    return rows


def append_row(path: Path, row: Row) -> None:
    if not path.exists() or not path.read_text(encoding="utf-8-sig").strip():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(",".join(HEADER) + "\n", encoding="utf-8")
    ended = path.read_text(encoding="utf-8").endswith("\n")  # a hand edit may drop the last line break
    with path.open("a", encoding="utf-8") as registry:
        registry.write(row.as_line() if ended else "\n" + row.as_line())


def next_number(category: Category, taken: list[str], report: str | None = None) -> str:
    """The number after the highest taken one: per category, or per report for an addendum category. Malformed
    numbers are skipped here (the check reports them)."""
    numbers = [n for n in taken if category.valid_number(n)]
    if isinstance(category, AddendumCategory):
        parts = [int(n.split(".")[1]) for n in numbers if n.split(".")[0] == report]
        return f"{report}.{max(parts, default=0) + 1}"
    return str(max((int(n) for n in numbers), default=0) + 1)
