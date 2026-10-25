"""Crash-safe file writes shared by a book's account (E1) and its desk journal (E4): an append is one line flushed to
disk; a rewrite goes through a temporary file and an atomic rename; a line without its newline is a write cut short by
a crash and is never read as data."""

from __future__ import annotations

import csv
import io
import os
from pathlib import Path


def csv_text(columns: tuple[str, ...], rows: list[dict], header: bool) -> str:
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=columns, lineterminator="\n")
    if header:
        writer.writeheader()
    writer.writerows(rows)
    return out.getvalue()


def complete_lines(text: str) -> str:
    """The text up to its last newline: a line without one is a write cut short by a crash."""
    return text[: text.rfind("\n") + 1]


def drop_partial_line(path: Path) -> None:
    """Cut a half-written last line off the file (after a crash), so the next append starts on a clean line."""
    text = path.read_text(encoding="utf-8")
    complete = complete_lines(text)
    if complete != text:
        with open(path, "r+b") as fh:
            fh.truncate(len(complete.encode("utf-8")))
            os.fsync(fh.fileno())


def append_durably(path: Path, text: str) -> None:
    with open(path, "a", encoding="utf-8", newline="") as fh:
        fh.write(text)
        fh.flush()
        os.fsync(fh.fileno())


def write_atomic(path: Path, temporary: Path, text: str) -> None:
    with open(temporary, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(temporary, path)
