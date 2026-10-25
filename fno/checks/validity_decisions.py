"""C4's own reading of the owner's decision rows a brake restart cites (story C5b; no `fno.risk` code): the title is
the first bold span of the row's Decision cell; the cited title must belong to exactly one row; that row quotes the
owner, names the book as a whole word ("Book 1"), is dated on or before the restart, and is cited by no other restart
of the book."""

from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path

from ..constants import BOOK_DISPLAY_NAMES

FIRST_BOLD = re.compile(r"\*\*(.+?)\*\*")


def decision_rows(path: Path) -> list[tuple[date, str | None, str]]:
    """(day, title or None, full line) of each dated table row."""
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        cells = line.split("|")
        if len(cells) < 4 or not line.startswith("| "):
            continue
        try:
            day = datetime.strptime(cells[1].strip(), "%d %b %Y").date()
        except ValueError:
            continue
        bold = FIRST_BOLD.search(cells[2])
        rows.append((day, bold.group(1) if bold else None, line))
    return rows


def decision_problem(rows, book: str, restarts: list[tuple[date, str]]) -> str | None:
    """The first reason a restart of `book` is not backed by one owner row, or None."""
    if restarts and book not in BOOK_DISPLAY_NAMES:
        return f"{book} is not named in the owner's decisions: no restart row can lift its brake"
    cited = [title for _, title in restarts]
    for day, title in restarts:
        found = [row for row in rows if title and row[1] == title]
        if len(found) != 1 or cited.count(title) > 1:
            return f"restart on {day}: decision {title!r} is not one uncited owner row ({len(found)} rows)"
        row_day, _, line = found[0]
        named = re.search(rf"\b{re.escape(BOOK_DISPLAY_NAMES[book])}\b", line)
        if '(owner: "' not in line or not named or row_day > day:
            return f"restart on {day}: decision {title!r} must quote the owner, name {BOOK_DISPLAY_NAMES[book]} and " \
                   f"be dated on or before the restart"  # fmt: skip
    return None
