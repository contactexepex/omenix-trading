"""An append-only CSV file whose rows are idempotent by a key column (story E4's desk records, like E1's ledger): the
same row again is a no-op, a different row under a used key is an error, and a line cut short by a crash is dropped."""

from __future__ import annotations

import csv
import io
from pathlib import Path

from ..books.files import append_durably, complete_lines, csv_text, drop_partial_line, write_atomic


class LogConflict(ValueError):
    """A key already records a different row."""


class IdempotentCsvLog:
    def __init__(self, path: Path, temporary: Path, columns: tuple[str, ...], key: str):
        self.path, self.temporary, self.columns, self.key = path, temporary, columns, key

    def rows(self) -> list[dict[str, str]]:
        if not self.path.exists():
            return []
        reader = csv.DictReader(io.StringIO(complete_lines(self.path.read_text(encoding="utf-8"))))
        if tuple(reader.fieldnames or ()) != self.columns:
            raise LogConflict(f"{self.path.name}: columns must be {self.columns}")
        return list(reader)

    def append(self, row: dict[str, str]) -> bool:
        """Record the row once: False when this exact row is already there."""
        if set(row) != set(self.columns):
            raise LogConflict(f"{self.path.name}: a row needs exactly the columns {self.columns}")
        if not self.path.exists():
            write_atomic(self.path, self.temporary, csv_text(self.columns, [], header=True))
        drop_partial_line(self.path)
        for old in self.rows():
            if old[self.key] == row[self.key]:
                if old == row:
                    return False
                raise LogConflict(f"{self.path.name}: {self.key} {row[self.key]} already records a different row")
        append_durably(self.path, csv_text(self.columns, [row], header=False))
        return True
