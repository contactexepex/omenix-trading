"""The monthly review rows that lift a driver's brake (story section 6 answer 5): `research/school/reviews/
brake_lifts.csv`, written by the orchestrator session on or after the first Saturday of the next month; no row, no
lift. Columns `reviewed_on, driver_id, review_ref`. A malformed file is an error, never read as "no lift" or as one."""

import csv
from datetime import date
from pathlib import Path
from typing import Protocol

REVIEWS_FILE = Path("research") / "school" / "reviews" / "brake_lifts.csv"
COLUMNS = ("reviewed_on", "driver_id", "review_ref")


class BrakeReviews(Protocol):
    def lifts(self, driver_id: str, before: date) -> tuple[date, ...]:
        """The review days that lift this driver's brake, dated strictly before `before` (no look-ahead)."""


class ReviewFileError(ValueError):
    """The review file cannot be read as its columns say."""


class ReviewFile:
    def __init__(self, path: Path):
        self.path = Path(path)

    def lifts(self, driver_id: str, before: date) -> tuple[date, ...]:
        if not self.path.exists():
            return ()
        with open(self.path, encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            if tuple(reader.fieldnames or ()) != COLUMNS:
                raise ReviewFileError(f"{self.path.name}: columns must be {', '.join(COLUMNS)}")
            rows = list(reader)
        days = [_day(row) for row in rows if row["driver_id"] == driver_id]
        return tuple(sorted(day for day in days if day < before))


def _day(row: dict[str, str]) -> date:
    if not row["review_ref"].strip():
        raise ReviewFileError(f"review row for {row['driver_id']} names no review")
    try:
        return date.fromisoformat(row["reviewed_on"])
    except ValueError as bad:
        raise ReviewFileError(f"review row for {row['driver_id']}: {row['reviewed_on']!r} is not a date") from bad
