"""The watcher's watcher (story O8): every run appends one row to `research/ops/health_runs.csv`; a later run reports
each calendar day of its window with no row, never a day before the file's first row (the first run has no history)."""

from __future__ import annotations

import csv
import io
from datetime import date, datetime
from pathlib import Path

from .window import window_days

COLUMNS = ("date", "started_at", "finished_at", "result")


class RunRecord:
    def __init__(self, path: Path):
        self.path = Path(path)

    def days_run(self) -> set[date]:
        if not self.path.is_file():
            return set()
        rows = csv.DictReader(io.StringIO(self.path.read_text(encoding="utf-8")))
        return {date.fromisoformat(row["date"]) for row in rows}

    def missing(self, run_day: date, days: int) -> list[date]:
        done = self.days_run()
        if not done:
            return []
        first = min(done)
        return [day for day in window_days(run_day, days) if day >= first and day not in done]

    def append(self, run_day: date, started: datetime, finished: datetime, result: str) -> None:
        new = not self.path.is_file()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a", encoding="utf-8", newline="") as fh:
            writer = csv.writer(fh, lineterminator="\n")
            if new:
                writer.writerow(COLUMNS)
            writer.writerow((run_day.isoformat(), started.isoformat(), finished.isoformat(), result))
