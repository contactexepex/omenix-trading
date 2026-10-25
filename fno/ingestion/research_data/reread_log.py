"""The append-only record of the daily re-read of recent participant-OI files (story A8 on GitHub Actions): one row per
due day whose re-read finished with every file answered. The re-read is recorded rather than inferred from the release
log, whose rows for earlier days also come from late runs checking the previous evening's file (judge 89)."""

from __future__ import annotations

import csv
from datetime import date, datetime
from pathlib import Path

FIELDS = ("day", "reread_at")


class RereadLog:
    def __init__(self, path: Path):
        self.path = Path(path)

    def done(self, day: date) -> bool:
        if not self.path.is_file():
            return False
        rows = csv.DictReader(self.path.read_text(encoding="utf-8").splitlines())
        return any(row["day"] == day.isoformat() for row in rows)

    def record(self, day: date, at: datetime) -> None:
        new = not self.path.is_file()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, lineterminator="\n")
            if new:
                writer.writerow(FIELDS)
            writer.writerow([day.isoformat(), at.isoformat()])
