"""The all-company announcement and board-meeting lists (story A12), one file per calendar day: archived by the existing
raw-data librarian (A9), which walks a calendar's days, so these lists get a calendar of every day (companies announce
on holidays and weekends too) and a content check.
"""

from __future__ import annotations

import json
from datetime import timedelta

from ..research_data.calendar import SessionCalendar
from ..storage.librarian import FillReport

EVERY_DAY = "calendar day"


class EveryDayCalendar(SessionCalendar):
    """Every calendar day counts: the lists are published for days, not trading sessions."""

    def session_kind(self, day) -> str:
        return EVERY_DAY

    def calendar_sha256(self) -> str:
        return EVERY_DAY


def check_day_list(filename: str, data: bytes) -> None:
    """A day's list is a JSON array of objects (an empty array is a day without announcements); ValueError if not."""
    try:
        rows = json.loads(data)
    except ValueError as exc:
        raise ValueError(f"{filename}: not JSON: {exc}") from exc
    if not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows):
        raise ValueError(f"{filename}: not a list of announcements")


CHUNK_DAYS = 30  # days filled between two looks at the clock


class TimeBudgetedFill:
    """Fills a day list in chunks and stops cleanly at its deadline, so a scheduled job ends by itself before
    GitHub's 6-hour limit instead of being killed; the next run starts at the first day still missing. Wraps any
    librarian with `fill(start, end)` (A9's `RawDataLibrarian`)."""

    def __init__(self, librarian, clock, deadline, chunk_days: int = CHUNK_DAYS):
        self.librarian, self.clock, self.deadline, self.chunk_days = librarian, clock, deadline, chunk_days

    def fill(self, start, end) -> FillReport:
        report = FillReport(self.librarian.source.dataset, start, end)
        while start <= end and self.clock() < self.deadline:
            chunk_end = min(end, start + timedelta(days=self.chunk_days - 1))
            _add(report, self.librarian.fill(start, chunk_end))
            start = chunk_end + timedelta(days=1)
        report.end = min(end, start - timedelta(days=1))  # the last day this run reached
        return report


def _add(total: FillReport, part: FillReport) -> None:
    total.sessions += part.sessions
    total.present += part.present
    total.excepted += part.excepted
    total.uploaded += part.uploaded
    total.damaged += part.damaged
    total.rejected += part.rejected
    total.not_published += part.not_published
