"""A report rewritten every run (O9b): written through one port, so where it lives is the composition root's choice.
`CsvReportFile` rewrites one repository file atomically (tests, and the files before a group moves);
`ReceiptedSnapshots` (`receipted_rows.py`) keeps one write-once Drive file per run with its receipt."""

from __future__ import annotations

import csv
import io
from abc import ABC, abstractmethod
from pathlib import Path


class Report(ABC):
    @abstractmethod
    def write(self, fields: tuple[str, ...], rows: list[tuple]) -> None:
        """The report's whole new content."""


class CsvReportFile(Report):
    def __init__(self, path: Path):
        self.path = Path(path)

    def write(self, fields: tuple[str, ...], rows: list[tuple]) -> None:
        out = io.StringIO()
        writer = csv.writer(out, lineterminator="\n")
        writer.writerow(fields)
        writer.writerows(rows)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(f".{self.path.name}.part")
        temporary.write_text(out.getvalue(), encoding="utf-8")
        temporary.replace(self.path)  # never a half-written report
