"""NSE's trading sessions, from one versioned file built from NSE's own circulars (never from the data files, so the
data can be checked against it). Every component asks `SessionCalendar`, never `weekday()`.

The file (`research/data/calendar/nse_sessions.csv`, columns `date,kind,description,source_url`) lists only the
exceptions to "every weekday is a regular session": weekday holidays (`holiday`), weekend live sessions (`special`)
and Diwali muhurat sessions (`muhurat`, a session whatever the day). It covers whole calendar years, from the first
to the last year it lists; every year in between must have rows, and every row a source link.
"""

from __future__ import annotations

import csv
import hashlib
from abc import ABC, abstractmethod
from datetime import date, timedelta
from pathlib import Path

from ..constants import SESSION_HOLIDAY as HOLIDAY
from ..constants import SESSION_MUHURAT as MUHURAT
from ..constants import SESSION_REGULAR as REGULAR
from ..constants import SESSION_SPECIAL as SPECIAL

ROW_KINDS = (HOLIDAY, SPECIAL, MUHURAT)
FIELDS = ("date", "kind", "description", "source_url")
SATURDAY = 5
OUTSIDE_RANGE = (
    "{day} is outside the calendar ({first} to {last}): add every row of NSE's {year} holiday circular (weekday "
    "holidays, weekend special sessions, the muhurat session), each with its https source link, to the calendar file"
)


class CalendarError(ValueError):
    """The calendar file is invalid, or a day outside the years it covers was asked about."""


class SessionCalendar(ABC):
    @abstractmethod
    def session_kind(self, day: date) -> str | None:
        """`regular`, `special` or `muhurat` for a session; None when the market is closed."""

    @abstractmethod
    def calendar_sha256(self) -> str:
        """Fingerprint of the calendar's source, recorded with every result that relies on it."""

    def is_session(self, day: date) -> bool:
        return self.session_kind(day) is not None

    def sessions(self, start: date, end: date) -> list[date]:
        """Every session from start to end, both included."""
        return [start + timedelta(n) for n in range((end - start).days + 1) if self.is_session(start + timedelta(n))]

    def previous_session(self, day: date) -> date:
        return self._step(day, -1)

    def next_session(self, day: date) -> date:
        return self._step(day, 1)

    def _step(self, day: date, direction: int) -> date:
        day += timedelta(direction)
        while not self.is_session(day):  # stops at the covered range: session_kind raises outside it
            day += timedelta(direction)
        return day


class CsvSessionCalendar(SessionCalendar):
    def __init__(self, text: str):
        self._sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
        self._kinds: dict[date, str] = {}
        rows = list(csv.DictReader(text.splitlines()))
        if not rows or tuple(rows[0]) != FIELDS:
            raise CalendarError(f"calendar needs the columns {','.join(FIELDS)} and at least one row")
        for number, row in enumerate(rows, start=2):
            self._add(number, row)
        years = {day.year for day in self._kinds}
        self.first, self.last = date(min(years), 1, 1), date(max(years), 12, 31)
        missing = sorted(set(range(self.first.year, self.last.year + 1)) - years)
        if missing:
            raise CalendarError(f"no rows for the years {missing}: the calendar cannot have gaps")

    def _add(self, number: int, row: dict) -> None:
        try:
            day = date.fromisoformat(row["date"])
        except (TypeError, ValueError) as exc:
            raise CalendarError(f"line {number}: bad date {row['date']!r}") from exc
        kind, source = row["kind"], (row["source_url"] or "").strip()
        if kind not in ROW_KINDS:
            raise CalendarError(f"line {number}: kind must be one of {ROW_KINDS}, not {kind!r}")
        if not source.startswith("https://"):
            raise CalendarError(f"line {number}: every row needs an https source link")
        if day in self._kinds:
            raise CalendarError(f"line {number}: {day} is listed twice")
        if kind == HOLIDAY and day.weekday() >= SATURDAY:
            raise CalendarError(f"line {number}: {day} is a weekend day; only weekday holidays are listed")
        if kind == SPECIAL and day.weekday() < SATURDAY:
            raise CalendarError(f"line {number}: {day} is a weekday; a special session is a weekend session")
        self._kinds[day] = kind

    def session_kind(self, day: date) -> str | None:
        if not self.first <= day <= self.last:
            raise CalendarError(OUTSIDE_RANGE.format(day=day, first=self.first, last=self.last, year=day.year))
        kind = self._kinds.get(day)
        if kind is None:
            return REGULAR if day.weekday() < SATURDAY else None
        return None if kind == HOLIDAY else kind

    def calendar_sha256(self) -> str:
        return self._sha256


def load_session_calendar(path: Path) -> CsvSessionCalendar:
    return CsvSessionCalendar(path.read_text(encoding="utf-8"))
