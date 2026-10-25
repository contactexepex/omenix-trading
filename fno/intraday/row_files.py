"""One CSV file per record (story A16, "Two checkouts, one ledger"): a header and one row, written once, never edited.
Two recorder runs in two clones never append to the same file, so their pushes cannot conflict on each other's rows;
the only possible clash is two first versions of the same record, which the committer settles by keeping the copy
already on GitHub (the first push)."""

from __future__ import annotations

import csv
import io
from pathlib import Path


class RowFileExists(ValueError):
    """The record already has its file; records are written once."""


def write_row(path: Path, fields: tuple[str, ...], row: dict) -> None:
    if path.exists():
        raise RowFileExists(f"{path.name} is already written: records are written once")
    path.parent.mkdir(parents=True, exist_ok=True)
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerow(row)
    temporary = path.with_name(f".{path.name}.part")
    temporary.write_text(out.getvalue(), encoding="utf-8")
    temporary.replace(path)  # never a half-written record under the real name


def read_rows(folder: Path, pattern: str) -> list[dict]:
    """Every record under `folder` matching the glob `pattern`, in file-name order."""
    rows = []
    for path in sorted(Path(folder).glob(pattern)):
        rows += list(csv.DictReader(io.StringIO(path.read_text(encoding="utf-8"))))
    return rows
