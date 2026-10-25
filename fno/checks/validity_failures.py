"""C4's failure log (story C4): every blocked trade appended to `journal/<book>/validity_failures.csv`, one row per
failed check, so a reader sees which check stopped which trade and why. Append-only, one durable line at a time."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from ..books.files import append_durably, csv_text, drop_partial_line
from ..books.paths import book_folder
from ..constants import VALIDITY_FAILURES_FILE
from .validity import ValidityReport

COLUMNS = ("day", "book", "opportunity_id", "mode", "check", "reason", "numbers")


class ValidityFailureLog:
    def __init__(self, root: Path):
        self.root = Path(root)

    def path(self, book: str) -> Path:
        return book_folder(self.root, book) / VALIDITY_FAILURES_FILE

    def append(self, day: date, report: ValidityReport) -> None:
        """One row per failed check of a failed report; a passing report writes nothing."""
        if report.ok:
            return
        path = self.path(report.book)
        path.parent.mkdir(parents=True, exist_ok=True)
        new = not path.exists()
        if not new:
            drop_partial_line(path)
        rows = [
            {"day": day.isoformat(), "book": report.book, "opportunity_id": report.opportunity_id,
             "mode": report.mode, "check": r.name, "reason": r.reason, "numbers": json.dumps(dict(r.numbers))}
            for r in report.failures
        ]  # fmt: skip
        append_durably(path, csv_text(COLUMNS, rows, header=new))
