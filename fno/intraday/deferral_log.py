"""Sessions the back-fill had to put off (story A16b): one row per run that deferred a session (time, session,
reason), so a day Groww keeps failing shows how many runs have deferred it (judge 122 addendum 4). A session once
written is never deferred again, so every row counts runs it waited through; a run whose range stops before the session
adds none, so the count is runs that tried, not calendar days. No automatic void: a stuck day stays visible until a
person decides."""

from __future__ import annotations

import csv
import io
from collections import Counter
from datetime import date, datetime
from pathlib import Path

FIELDS = ("deferred_at", "session", "reason")


class DeferralLog:
    def __init__(self, path: Path):
        self.path = Path(path)

    def counts(self) -> Counter:
        if not self.path.is_file():
            return Counter()
        return Counter(r["session"] for r in csv.DictReader(io.StringIO(self.path.read_text(encoding="utf-8"))))

    def append(self, at: datetime, deferred: dict[date, str]) -> None:
        if not deferred:
            return
        new = not self.path.is_file() or not self.path.stat().st_size
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, lineterminator="\n")
            if new:
                writer.writerow(FIELDS)
            writer.writerows((at.isoformat(), day.isoformat(), reason) for day, reason in sorted(deferred.items()))
