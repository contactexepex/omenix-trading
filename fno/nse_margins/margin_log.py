"""`research/data/margins/margins.csv` as an append-only log (story A14): rows are only ever added at the end.

The same row again is a no-op; any other row for an existing (structure, width, as_of) is a conflict and nothing is
written (C2 reads the latest row on or before a day, so two figures for one day would be ambiguous). The file's bytes
before an append are always a prefix of the file after it.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Sequence
from datetime import date
from pathlib import Path

from ..risk.margins import MARGIN_COLUMNS
from .rows import MarginRow


class MarginLogConflict(RuntimeError):
    """A row would contradict one already in the log; nothing was written."""


def _key(row: dict[str, str]) -> tuple[str, float, str]:
    return row["structure"], float(row["width"]), row["as_of"]


class MarginLog:
    def __init__(self, path: Path):
        self.path = Path(path)

    def existing(self) -> list[dict[str, str]]:
        if not self.path.is_file():
            raise MarginLogConflict(f"{self.path.name} is missing (it is created with its header, never by a job)")
        reader = csv.DictReader(io.StringIO(self.path.read_text(encoding="utf-8")))
        if tuple(reader.fieldnames or ()) != MARGIN_COLUMNS:
            raise MarginLogConflict(f"{self.path.name}: columns must be {', '.join(MARGIN_COLUMNS)}")
        return list(reader)

    def days_from(self, source_prefix: str) -> set[date]:
        """The days that already have a row whose source starts with `source_prefix`."""
        return {date.fromisoformat(r["as_of"]) for r in self.existing() if r["source"].startswith(source_prefix)}

    def append(self, rows: Sequence[MarginRow]) -> int:
        """Adds the new rows at the end; returns how many were added. MarginLogConflict writes nothing."""
        known = {_key(r): r for r in self.existing()}
        new = []
        for row in (r.as_csv() for r in rows):
            if known.get(_key(row)) == row:
                continue
            if _key(row) in known:
                raise MarginLogConflict(f"{self.path.name} already has a different row for {_key(row)}")
            known[_key(row)] = row
            new.append(row)
        if new:
            self._write_at_end(new)
        return len(new)

    def _write_at_end(self, rows: list[dict[str, str]]) -> None:
        text = self.path.read_text(encoding="utf-8")
        out = io.StringIO()
        if text and not text.endswith("\n"):
            out.write("\n")
        csv.DictWriter(out, MARGIN_COLUMNS, lineterminator="\n").writerows(rows)
        with open(self.path, "a", encoding="utf-8", newline="") as fh:
            fh.write(out.getvalue())
