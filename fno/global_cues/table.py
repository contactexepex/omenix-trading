"""A cue's derived daily table (story A17): one row per value date, append-only, with the SHA-256 of the archived copy
it came from, when we first saw it, and whether it was seen in time to be used live.

- `first_seen_at`: when the copy holding the value was fetched (IST).
- `provenance`: `live` when first seen before 09:15 IST on the first NSE session after the value date (the earliest
  open that could use it), else `backfilled`: history fetched later, never known at the time by this tool.
- A new date after the table's last one is appended. A date already held with the same value is skipped; with another
  value the table keeps its row and the change is logged in its revision log (`changed`); a date before the last one
  that the table lacks (a late publication) is logged (`late`) and never inserted. Rows already held never change.
- Where the rows live is the `RowLog`'s business (`fno/storage/row_log.py`): a repository CSV, or Drive only
  for private cues.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, time

from ..models import IST
from ..storage.row_log import RowLog
from .collection import SourcedValue

FIELDS = ("value_date", "value", "source_sha256", "first_seen_at", "provenance")
REVISION_FIELDS = ("cue", "value_date", "kind", "table_value", "new_value", "source_sha256", "seen_at")
NSE_OPEN = time(9, 15)
LIVE, BACKFILLED = "live", "backfilled"
CHANGED, LATE = "changed", "late"


@dataclass
class MergeResult:
    added: int = 0
    revisions: int = 0  # new revision rows logged this time


def provenance(value_date: date, seen_at: datetime, next_session: Callable[[date], date]) -> str:
    """`live` when seen before the first NSE open after the value date, else `backfilled`."""
    first_use = datetime.combine(next_session(value_date), NSE_OPEN, tzinfo=IST)
    return LIVE if seen_at < first_use else BACKFILLED


class CueTable:
    def __init__(self, cue: str, rows: RowLog, revisions: RowLog, next_session: Callable[[date], date]):
        """`rows` holds this cue's table; `revisions` its revision log (shared with other cues where they agree)."""
        self.cue, self.log, self.revision_log, self.next_session = cue, rows, revisions, next_session

    def rows(self) -> list[dict[str, str]]:
        return self.log.rows()

    def merge(self, values: list[SourcedValue], seen_at: datetime) -> MergeResult:
        held = {r["value_date"]: r for r in self.rows()}
        logged = {_key(r["cue"], r["value_date"], r["kind"], r["new_value"]) for r in self.revision_log.rows()}
        last = max(held, default="")
        new_rows, revisions = [], []
        for sourced in sorted(values, key=lambda s: s.value.value_date):
            day, value = sourced.value.value_date.isoformat(), sourced.value.value
            if day in held and float(held[day]["value"]) == value:
                continue
            if day in held or day < last:
                kind, table_value = (CHANGED, held[day]["value"]) if day in held else (LATE, "")
                if _key(self.cue, day, kind, value) not in logged:
                    logged.add(_key(self.cue, day, kind, value))
                    revisions.append((self.cue, day, kind, table_value, repr(value), sourced.source_sha256, seen_at))
                continue
            status = provenance(sourced.value.value_date, seen_at, self.next_session)
            new_rows.append((day, repr(value), sourced.source_sha256, seen_at.isoformat(), status))
            last = day
        self.log.check_appendable()  # both logs first: never a row written and its revision lost
        self.revision_log.check_appendable()
        self.log.append(FIELDS, new_rows)
        self.revision_log.append(REVISION_FIELDS, [(*r[:-1], r[-1].isoformat()) for r in revisions])
        return MergeResult(len(new_rows), len(revisions))


def _key(cue: str, day: str, kind: str, value) -> tuple:
    return cue, day, kind, float(value)
