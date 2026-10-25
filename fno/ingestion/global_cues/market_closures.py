"""A foreign market's whole-day closures (story A17f, DR1 item 8): the weekdays it does not trade, from its exchange's
published holiday file, plus closures announced on the day (a typhoon), each with its source. Part B asks it before
reading an index, so a listed closure is `market closed` with no request.

The file (`research/data/calendar/twse_closures.csv`, columns `date,kind,description,source_url,sha256`) has three
kinds: `covers` (one row per year the file is complete for: 1 Jan of that year and the SHA-256 of the exchange's file
it was copied from), `holiday` (a published closure) and `unscheduled` (one announced late). Rows are keyed by date and
kind, so a year's `covers` row and a 1 Jan `holiday` row live side by side. A closure in a year without a `covers` row
is refused: a year is either complete or not used.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

COVERS, HOLIDAY, UNSCHEDULED = "covers", "holiday", "unscheduled"
CLOSURE_KINDS = (HOLIDAY, UNSCHEDULED)
FIELDS = ("date", "kind", "description", "source_url", "sha256")
ROC_OFFSET = 1911  # TWSE dates are Republic of China years: 115 is 2026
TRADING_DAY_MARK = "交易日"  # "trading day": TWSE's first and last trading-day rows, not closures
SATURDAY = 5


@dataclass(frozen=True)
class Closure:
    day: date
    kind: str
    description: str


class MarketClosures:
    def __init__(self, rows: list[dict[str, str]], name: str):
        """`rows`: the file's rows; ValueError naming the row when one is malformed, of an unknown kind, given twice,
        or a closure in a year the file does not cover."""
        self.name, self._covered, self._closures = name, set(), {}
        keyed = [(_day(row, n, name), row.get("kind", ""), row, n) for n, row in enumerate(rows, start=2)]
        for day, kind, _, n in keyed:
            if kind == COVERS and ((day.month, day.day) != (1, 1) or day.year in self._covered):
                raise ValueError(f"{name}: row {n} is not the only covers row of {day.year} on 1 Jan")
            if kind == COVERS:
                self._covered.add(day.year)
            elif kind not in CLOSURE_KINDS:
                raise ValueError(f"{name}: row {n} has an unknown kind {kind!r}")
        for day, kind, row, n in keyed:
            if kind == COVERS:
                continue
            if day.year not in self._covered:
                raise ValueError(f"{name}: row {n} is a closure in {day.year}, which has no covers row")
            if day in self._closures:
                raise ValueError(f"{name}: row {n} lists {day} twice")
            self._closures[day] = Closure(day, kind, row.get("description", ""))

    def covers(self, year: int) -> bool:
        return year in self._covered

    def closure(self, day: date) -> Closure | None:
        """The weekday closure on `day`, if any (weekends are closed anyway and never listed)."""
        return self._closures.get(day) if day.weekday() < SATURDAY else None


def load_closures(path: Path, name: str) -> MarketClosures:
    with open(path, encoding="utf-8") as f:
        return MarketClosures(list(csv.DictReader(f)), name)


def twse_closures(data: bytes) -> list[tuple[date, str]]:
    """The weekday closures in TWSE's holiday file (OpenAPI `holidaySchedule`): (date, TWSE's name). Rows whose name
    marks a first or last trading day are trading days; weekend rows are dropped. ValueError on a changed layout or an
    empty list (TWSE never publishes an empty year)."""
    try:
        rows = [(_roc_day(row["Date"]), row["Name"]) for row in json.loads(data)]
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"not TWSE's holiday file ({type(exc).__name__})") from exc
    if not rows:
        raise ValueError("TWSE's holiday file lists no day")
    return [(day, name) for day, name in rows if TRADING_DAY_MARK not in name and day.weekday() < SATURDAY]


def _roc_day(text: str) -> date:
    if len(text) != 7 or not text.isdigit():
        raise ValueError(f"{text!r} is not a TWSE date")
    return date(int(text[:3]) + ROC_OFFSET, int(text[3:5]), int(text[5:]))


def _day(row: dict[str, str], n: int, name: str) -> date:
    try:
        return date.fromisoformat(row.get("date") or "")
    except ValueError:
        raise ValueError(f"{name}: row {n} has no valid date") from None
