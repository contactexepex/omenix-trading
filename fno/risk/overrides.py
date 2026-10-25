"""The owner's written restarts of a book's drawdown brake: `journal/<book>/owner_overrides.csv` (story C2, design 8).

Columns `date, action, reason, entered_by, decision`; the only action is `restart_brake`. `decision` cites the owner's
row in `docs/DESK_DECISIONS.md` by its title (story C5b, `decision_rows.py`). The owner commits the row; the code only
reads it. A malformed row or a citation that fails a rule is an error (the brake then fails closed), and a row dated
after the decision day is not yet in force.
"""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from ..books.paths import book_folder, file_in_account
from ..constants import DESK_DECISIONS_FILE, OVERRIDE_RESTART_BRAKE, OWNER_OVERRIDES_FILE
from .decision_rows import RestartDecisions, read_decision_rows
from .inputs import RiskInputError

OVERRIDE_COLUMNS = ("date", "action", "reason", "entered_by", "decision")


def overrides_file(root: Path, book: str) -> Path:
    """The book's own overrides file; the book-path firewall refuses other books' folders and escaping links."""
    return file_in_account(book_folder(root, book), OWNER_OVERRIDES_FILE)


def _restart_day(row: dict[str, str], line: int) -> date:
    if row["action"] != OVERRIDE_RESTART_BRAKE:
        raise RiskInputError(f"{OWNER_OVERRIDES_FILE} line {line}: unknown action {row['action']!r}")
    if not row["reason"].strip() or not row["entered_by"].strip():
        raise RiskInputError(f"{OWNER_OVERRIDES_FILE} line {line}: reason and entered_by are required")
    try:
        return date.fromisoformat(row["date"])
    except ValueError as error:
        raise RiskInputError(f"{OWNER_OVERRIDES_FILE} line {line}: bad date {row['date']!r}") from error


def brake_restarts(root: Path, book: str, day: date) -> tuple[date, ...]:
    """The book's restart days up to and including `day`, oldest first; none when the file does not exist."""
    path = overrides_file(root, book)
    if not path.exists():
        return ()
    with open(path, encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        if tuple(reader.fieldnames or ()) != OVERRIDE_COLUMNS:
            raise RiskInputError(f"{path}: columns must be {', '.join(OVERRIDE_COLUMNS)}")
        restarts = [
            (_restart_day(row, line), (row["decision"] or "").strip()) for line, row in enumerate(reader, start=2)
        ]
    RestartDecisions(read_decision_rows(root / DESK_DECISIONS_FILE)).check(book, restarts)
    return tuple(sorted(d for d, _ in restarts if d <= day))
