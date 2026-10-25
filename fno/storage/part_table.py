"""A table that grows without ever changing a file (story O9, rule 2): each write is a new part
`<table>/<YYYY>/<MM>/<YYYY-MM-DD>.<run_id>.csv` saved through the DataStore, and the table is the union of its parts.
What a later part means for an earlier row (a correction, a newer value) stays each table's own rule, as today."""

from __future__ import annotations

import csv
import io
from collections.abc import Iterable, Sequence
from datetime import date
from pathlib import Path

from .data_store import DataStore
from .raw_store import path_parts
from .receipts import Receipt

PART_SUFFIX = ".csv"
COLUMNS_DIFFER = "{file}: columns {found} differ from the table's {expected}"


def part_path(table: str, day: date, run_id: str) -> str:
    return f"{table}/{day:%Y}/{day:%m}/{day:%Y-%m-%d}.{run_id}{PART_SUFFIX}"


def part_bytes(columns: Sequence[str], rows: Iterable[dict]) -> bytes:
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=list(columns), lineterminator="\n")  # the repository's CSV style
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue().encode("utf-8")


class PartTable:
    def __init__(self, store: DataStore, table: str, columns: Sequence[str]):
        path_parts(table)
        self.store, self.table, self.columns = store, table, tuple(columns)

    def write(self, day: date, rows: Iterable[dict]) -> Receipt:
        """One new part for `day` from this run (its run_id names it, so two runs never write the same file)."""
        return self.store.put(part_path(self.table, day, self.store.run_id), part_bytes(self.columns, rows))


def read_parts(folder: Path, columns: Sequence[str]) -> list[dict]:
    """Every row of every part under a table's folder on disk (the Drive cache), parts in path order, so rows come
    by day then by run. A part with other columns is refused rather than read wrongly."""
    rows: list[dict] = []
    for file in sorted(f for f in Path(folder).rglob(f"*{PART_SUFFIX}") if not f.name.startswith(".")):
        reader = csv.DictReader(io.StringIO(file.read_text(encoding="utf-8")))
        if tuple(reader.fieldnames or ()) != tuple(columns):
            raise ValueError(COLUMNS_DIFFER.format(file=file, found=reader.fieldnames, expected=list(columns)))
        rows += list(reader)
    return rows
