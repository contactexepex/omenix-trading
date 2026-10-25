"""The committed capture-error log (story O10): one row per failed capture, so every failure can be fixed from the
repository and not only from a Slack line or an Actions log that expires. Rows are appended, never edited.

A message is one line of at most `MAX_MESSAGE` characters and is built by the caller from names it knows (a workflow's
step name, a health check's reason), never from a log, so no secret can enter it."""

from __future__ import annotations

import csv
import io
from dataclasses import astuple, dataclass
from datetime import date
from pathlib import Path

CAPTURE_ERRORS_FILE = "research/ops/capture_errors.csv"  # beside O8's run record; committed by the watcher
COLUMNS = ("date", "job", "step", "kind", "message", "run_url")
MAX_MESSAGE = 200


def one_line(text: str, limit: int = MAX_MESSAGE) -> str:
    return " ".join(text.split())[:limit]


@dataclass(frozen=True)
class CaptureError:
    day: date
    job: str
    step: str
    kind: str
    message: str
    run_url: str

    def row(self) -> tuple[str, ...]:
        return (self.day.isoformat(), *(one_line(value) for value in astuple(self)[1:]))


class CaptureErrorLog:
    def __init__(self, path: Path):
        self.path = Path(path)

    def rows(self) -> list[CaptureError]:
        if not self.path.is_file():
            return []
        reader = csv.DictReader(io.StringIO(self.path.read_text(encoding="utf-8")))
        return [CaptureError(date.fromisoformat(r["date"]), *(r[c] for c in COLUMNS[1:])) for r in reader]

    def has_run(self, run_url: str, kind: str) -> bool:
        """The watcher's row for this run: other rows may share the URL (a long run records its own episodes)."""
        return any((error.run_url, error.kind) == (run_url, kind) for error in self.rows())

    def has(self, day: date, job: str, kind: str) -> bool:
        return any((e.day, e.job, e.kind) == (day, job, kind) for e in self.rows())

    def append(self, error: CaptureError) -> None:
        new = not self.path.is_file()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a", encoding="utf-8", newline="") as fh:
            writer = csv.writer(fh, lineterminator="\n")
            if new:
                writer.writerow(COLUMNS)
            writer.writerow(error.row())
