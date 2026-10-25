"""The derived India VIX daily table (story A15; in Drive with receipts since O9b): one row per day NSE published,
copied from the month file first archived in Drive (never from a later revision), with that file's archive path and
SHA-256 and the time this table first held the row.

Append-only: rows are only added after the table's last day (a new write-once part each run), so its earlier bytes
never change. A day already present with the same values is skipped; with other values it is refused (VixTableConflict),
as is a day before the last one that the table does not hold (a hole is never filled from behind).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from ..storage.row_log import RowLog, TableFileBroken
from .month_file import VixDay

FIELDS = ("date", "open", "high", "low", "close", "source_path", "source_sha256", "first_seen_at")
VALUE_FIELDS = FIELDS[:7]  # first_seen_at says when we got the row; it is not part of its values


class VixTableConflict(RuntimeError):
    """A day the table already holds came back different, or a day would be added behind the table's last day."""


@dataclass(frozen=True)
class VixRow:
    day: VixDay
    source_path: str
    source_sha256: str
    first_seen_at: datetime

    def cells(self) -> tuple[str, ...]:
        return (*value_cells(self.day, self.source_path, self.source_sha256), self.first_seen_at.isoformat())


def value_cells(day: VixDay, source_path: str, source_sha256: str) -> tuple[str, ...]:
    """A day's cells before `first_seen_at`, as the table writes them (NSE's values, never rounded)."""
    levels = (repr(day.open), repr(day.high), repr(day.low), repr(day.close))
    return (day.day.isoformat(), *levels, source_path, source_sha256)


class VixDailyTable:
    def __init__(self, rows: RowLog):
        """`rows`: where the table lives (O9b: write-once Drive parts with receipts; a repository CSV in tests)."""
        self.log = rows

    def rows(self) -> list[dict[str, str]]:
        return self.log.rows()

    def last_day(self) -> date | None:
        rows = self.rows()
        return date.fromisoformat(rows[-1]["date"]) if rows else None

    def append(self, new: list[VixRow]) -> int:
        """Adds the rows after the table's last day, in date order; returns how many were added."""
        held = {r["date"]: tuple(r[f] for f in VALUE_FIELDS) for r in self.rows()}
        last = max(held, default="")
        added = []
        for row in sorted(new, key=lambda r: r.day.day):
            cells = row.cells()
            if cells[0] in held:
                if held[cells[0]] != cells[: len(VALUE_FIELDS)]:
                    raise VixTableConflict(f"{cells[0]}: the table already holds other values for this day")
                continue
            if cells[0] < last:
                raise VixTableConflict(f"{cells[0]}: before the table's last day {last}; a hole is never filled")
            added.append(cells)
            last = cells[0]
        if added:
            try:
                self.log.check_appendable()
            except TableFileBroken as exc:
                raise VixTableConflict(str(exc)) from exc
            self.log.append(FIELDS, added)
        return len(added)
