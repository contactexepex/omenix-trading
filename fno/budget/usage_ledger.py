"""The AI usage ledger `accounting/ai_usage.csv` (story F8): one row per AI session per IST day, written once and never
rewritten. Rows come only from a `SessionUsageReader`; only days the reader calls complete are recorded (before today,
and before the day an export was taken), each with the day before which its reading was complete. A session is known by
its id without the prefix (`session_` or `cse_`), so the same session written two ways is still recorded once. The file
is rewritten whole through a temporary file, never appended in place. Two recorders, no lock: a development session
(`budget record-usage`) and `ai collect` in its Actions job (story F8c). A push that meets the other's change on this
file is refused by git, never merged into a wrong file; recording again is safe, since a session-day is written once."""

from __future__ import annotations

import csv
import io
import math
import os
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from ..constants import AI_BOOKS
from .constants import PURPOSE_BOOKS_AND_ROLES, USAGE_PURPOSES
from .usage_export import TOKEN_FIELDS
from .usage_reader import DayUsage

LEDGER_FILE = "accounting/ai_usage.csv"
COLUMNS = ("date", "purpose", "book", "role_or_bundle", "session_id", "model", "minutes", "wait_minutes", "turns",
           *TOKEN_FIELDS, "tokens_basis", "source", "complete_before")  # fmt: skip
TOKENS_BASIS = "main-loop usage of result events (side calls not included)"
NOT_COMPLETE = "{day} is not complete in this reading (complete days are before {before}): record it from a later one"
BAD_ROW = "{file} line {line}: minutes {minutes!r} is not a number >= 0, or complete_before is not a date"
WAIT_APART = " (and a wait of {wait} minutes apart, not capped)"  # BG1-w
BAD_WAIT = "{file} line {line}: wait_minutes {wait!r} is not blank or a number >= 0"
SESSION_ID = re.compile(r"session_[A-Za-z0-9]+")  # get_session's id form


def session_key(session: str) -> str:
    """`https://claude.ai/code/cse_01X`, `cse_01X` and `session_01X` all give `01X`."""
    return session.strip().rstrip("/").rsplit("/", 1)[-1].split("_", 1)[-1]


class UsageRefused(ValueError):
    """The row cannot be recorded; the message says why."""


@dataclass(frozen=True)
class Attribution:
    """Who the session worked for: books and roles (counts against the cap) or development."""

    purpose: str
    book: str = ""  # an AI book for a book's session, else empty
    role_or_bundle: str = ""

    def check(self) -> None:
        if self.purpose not in USAGE_PURPOSES:
            raise UsageRefused(f"purpose must be one of {USAGE_PURPOSES}, not {self.purpose!r}")
        if self.book and self.book not in AI_BOOKS:
            raise UsageRefused(f"book must be one of {AI_BOOKS} or empty, not {self.book!r}")
        if self.book and self.purpose != PURPOSE_BOOKS_AND_ROLES:
            raise UsageRefused("a book's session is books_and_roles use")
        if not (self.book or self.role_or_bundle):
            raise UsageRefused("name the book or the role (or bundle) the session worked for")


class UsageLedger:
    def __init__(self, root: Path):
        self._path = root / LEDGER_FILE

    def rows(self) -> list[dict]:
        if not self._path.is_file():
            return []
        reader = csv.DictReader(io.StringIO(self._path.read_text(encoding="utf-8")))
        if tuple(reader.fieldnames or ()) != COLUMNS:
            raise ValueError(f"{LEDGER_FILE} columns must be {COLUMNS}")
        rows = list(reader)
        for line, row in enumerate(rows, start=2):
            _check_row(line, row)
        return rows

    def record(self, days: list[DayUsage], who: Attribution, before: date) -> list[str]:
        """Adds the days before `before` not recorded yet; returns one line per day (recorded or why not)."""
        who.check()
        rows = self.rows()
        known = {(session_key(row["session_id"]), row["date"]) for row in rows}
        lines, new = [], []
        for usage in days:
            if not SESSION_ID.fullmatch(usage.session_id):
                raise UsageRefused(f"session id {usage.session_id!r} is not of the form session_<letters and digits>")
            if usage.day >= before:
                lines.append(NOT_COMPLETE.format(day=usage.day, before=before))
            elif (session_key(usage.session_id), usage.day.isoformat()) in known:
                lines.append(f"{usage.day} {usage.session_id}: already recorded (never rewritten)")
            else:
                new.append(_row(usage, who, before))
                wait = "" if usage.wait_minutes is None else WAIT_APART.format(wait=usage.wait_minutes)
                lines.append(
                    f"{usage.day} {usage.session_id}: recorded {usage.minutes} minutes{wait}, {usage.turns} turns"
                )
        if new:
            self._write(rows + new)
        return lines

    def _write(self, rows: list[dict]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        out = io.StringIO()
        writer = csv.DictWriter(out, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        temporary = self._path.with_suffix(".csv.tmp")
        temporary.write_text(out.getvalue(), encoding="utf-8")
        os.replace(temporary, self._path)  # all or nothing: a crash never leaves half a row


def _check_row(line: int, row: dict) -> None:
    if None in row or None in row.values():
        raise ValueError(f"{LEDGER_FILE} line {line}: wrong number of fields")
    try:
        date.fromisoformat(row["complete_before"])
    except ValueError:
        raise ValueError(BAD_ROW.format(file=LEDGER_FILE, line=line, minutes=row["minutes"])) from None
    if not _non_negative(row["minutes"]):
        raise ValueError(BAD_ROW.format(file=LEDGER_FILE, line=line, minutes=row["minutes"]))
    if row["wait_minutes"] != "" and not _non_negative(row["wait_minutes"]):  # BG1-w: blank, not measured apart
        raise ValueError(BAD_WAIT.format(file=LEDGER_FILE, line=line, wait=row["wait_minutes"]))


def _non_negative(text: str) -> bool:
    try:
        return 0 <= float(text) < math.inf  # refuses nan and inf too
    except ValueError:
        return False


def _row(usage: DayUsage, who: Attribution, before: date) -> dict:
    """`complete_before`: every day of this session before it was complete in the reading the row came from, so a later
    check knows which of the session's days the ledger holds in full."""
    tokens = usage.tokens or {}
    row = {"date": usage.day.isoformat(), "purpose": who.purpose, "book": who.book,
           "role_or_bundle": who.role_or_bundle, "session_id": usage.session_id, "model": usage.model,
           "minutes": f"{usage.minutes:.2f}", "turns": usage.turns,
           "wait_minutes": "" if usage.wait_minutes is None else f"{usage.wait_minutes:.2f}"}  # fmt: skip
    row |= {column: tokens.get(column, "") for column in TOKEN_FIELDS}  # blank: unknown, never zero
    basis = TOKENS_BASIS if usage.tokens else "not available"
    return row | {"tokens_basis": basis, "source": usage.source, "complete_before": before.isoformat()}
