"""The owner's decision rows a brake restart must cite (story C5b): `docs/DESK_DECISIONS.md`, read, never written.

Each table row has a date and a Decision cell in the standard form `**title** (owner: "...")`. A row's title is the
first bold span of that cell; a row without one cannot be cited. A restart row of a book is valid only when its cited
title belongs to exactly one row, and that row quotes the owner, names the book as a whole word ("Book 1"), is dated on
or before the restart, and is cited by no other restart of that book. Which brake episode the words restart is judged
by the judge's audit, not by code.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from ..constants import BOOK_DISPLAY_NAMES
from .inputs import RiskInputError

TITLE = re.compile(r"\*\*(.+?)\*\*")
OWNER_WORDS = '(owner: "'
DATE_FORMAT = "%d %b %Y"  # "15 Oct 2026"


@dataclass(frozen=True)
class DecisionRow:
    day: date
    title: str | None  # the first bold span of the Decision cell; None: not citable
    text: str


def read_decision_rows(path: Path) -> list[DecisionRow]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        cells = line.split("|")
        if not line.startswith("| ") or len(cells) < 4:
            continue
        try:
            day = datetime.strptime(cells[1].strip(), DATE_FORMAT).date()
        except ValueError:
            continue  # the header row and its rule
        title = TITLE.search(cells[2])
        rows.append(DecisionRow(day, title.group(1) if title else None, line))
    return rows


class RestartDecisions:
    def __init__(self, rows: Sequence[DecisionRow]):
        self.rows = tuple(rows)

    def check(self, book: str, restarts: Sequence[tuple[date, str]]) -> None:
        """Each (restart day, cited title) of `book`; RiskInputError naming the first problem."""
        if restarts and book not in BOOK_DISPLAY_NAMES:
            raise RiskInputError(f"{book} is not named in the owner's decisions: no restart row can lift its brake")
        titles = [title for _, title in restarts]
        for day, title in restarts:
            if titles.count(title) > 1:
                raise RiskInputError(f"decision {title!r} is cited by more than one restart of {book}")
            self._row(book, day, title)

    def _row(self, book: str, day: date, title: str) -> DecisionRow:
        if not title:
            raise RiskInputError(f"restart of {book} on {day} cites no decision")
        found = [row for row in self.rows if row.title == title]
        if len(found) != 1:
            raise RiskInputError(f"decision {title!r} is the title of {len(found)} rows, not exactly one")
        row = found[0]
        if OWNER_WORDS not in row.text:
            raise RiskInputError(f"decision {title!r} does not quote the owner")
        if not re.search(rf"\b{re.escape(BOOK_DISPLAY_NAMES[book])}\b", row.text):
            raise RiskInputError(f"decision {title!r} does not name {BOOK_DISPLAY_NAMES[book]}")
        if row.day > day:
            raise RiskInputError(f"decision {title!r} of {row.day} is dated after the restart on {day}")
        return row
