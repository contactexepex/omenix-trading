"""A cue reading with its age and expected date (story A17b): what every consumer (M1, the weather, forecasts) uses.

`reading_for` takes the row `value_for` gives and says whether it is the one the publisher should have given by the
cutoff. Statuses, decided in this order:
- `none`: nothing usable;
- `current`: the expected date's value, whatever its age (after Hurricane Sandy, 26 Oct 2012 is current on 31 Oct);
- `ahead`: newer than the expected date (a value the calendar did not expect, e.g. RBI on an NSE holiday); usable like
  `current`, flagged so the calendar mismatch is seen;
- `behind`: older than the expected date, age within the source's `max_age_days`;
- `stale`: older than the expected date and over `max_age_days`.
A cue without a calendar (Brent) has no expected date: `behind` within `max_age_days`, else `stale`, or `none`.
Callers refuse `stale` and `none`, and state in their own rules any use of `behind`.

Rows on dates the calendar says are not sessions are skipped for a source that publishes holiday rows (Nasdaq's
repeat the previous close on US holidays), so the day after a US holiday never reads `ahead` with a repeated value.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

from ..models import IST
from .as_of import value_for
from .cue_calendars import CueCalendar
from .source import GlobalCueSource
from .table import CueTable

NONE, CURRENT, AHEAD, BEHIND, STALE = "none", "current", "ahead", "behind", "stale"
SEARCH_DAYS = 40  # how far back an expected date is looked for (no calendar has 40 closed days in a row)


@dataclass(frozen=True)
class CueReading:
    row: dict[str, str] | None = field(repr=False)  # holds the value: never printed (private cues, owner a927390)
    status: str
    age_days: int | None  # India date minus value date, in calendar days
    expected: date | None  # the date the publisher should have given by the cutoff (None: no calendar)


class CueReader:
    """A cue's reading from its table, source and calendar: the one way a consumer reads a cue."""

    def __init__(
        self,
        tables: dict[str, CueTable],
        sources: dict[str, GlobalCueSource],
        calendars: dict[str, CueCalendar | None],
    ):
        self.tables, self.sources, self.calendars = tables, sources, calendars

    def read(self, cue: str, india_day: date, cutoff: time, live_only: bool) -> CueReading:
        if cue not in self.tables:
            raise KeyError(f"{cue}: no table loaded (a private cue needs the Drive settings)")
        rows = self.tables[cue].rows()
        return reading_for(rows, india_day, cutoff, live_only, self.sources[cue], self.calendars[cue])


def reading_for(
    rows: list[dict[str, str]],
    india_day: date,
    cutoff: time,
    live_only: bool,
    source: GlobalCueSource,
    calendar: CueCalendar | None,
) -> CueReading:
    # a row dated after the India date is bad data (or a wrong first_seen_at): never usable, whatever the view
    rows = [r for r in rows if date.fromisoformat(r["value_date"]) <= india_day]
    if calendar is not None and source.holiday_rows:
        rows = [r for r in rows if calendar.is_session(date.fromisoformat(r["value_date"]))]
    expected = None if calendar is None else expected_date(india_day, cutoff, source, calendar)
    row = value_for(rows, india_day, cutoff, live_only, source.available_at)
    if row is None:
        return CueReading(None, NONE, None, expected)
    value_date = date.fromisoformat(row["value_date"])
    age = (india_day - value_date).days
    return CueReading(row, _status(value_date, age, expected, source.max_age_days), age, expected)


def _status(value_date: date, age: int, expected: date | None, max_age: int) -> str:
    if expected is not None and value_date == expected:
        return CURRENT
    if expected is not None and value_date > expected:
        return AHEAD
    return BEHIND if age <= max_age else STALE


def expected_date(india_day: date, cutoff: time, source: GlobalCueSource, calendar: CueCalendar) -> date:
    """The latest session whose value the source publishes before the cutoff on the India date."""
    moment = datetime.combine(india_day, cutoff, tzinfo=IST)
    for back in range(SEARCH_DAYS):
        day = india_day - timedelta(days=back)
        if calendar.is_session(day) and source.available_at(day) < moment:
            return day
    raise ValueError(f"{source.cue}: no session in the {SEARCH_DAYS} days to {india_day}: the calendar is broken")
