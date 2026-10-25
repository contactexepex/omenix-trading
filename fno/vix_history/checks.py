"""Checks of the India VIX table (story A15). Each lists what it finds and changes nothing: a gap is never filled, a
mismatch never corrected, a doubtful day never dropped.

- gaps: against NSE's session calendar, a session without a row and a row on a closed day; a row on a muhurat or
  special session (not a regular full day: select regular sessions through the A7 calendar); before the calendar's
  first year (2017) a weekday without a row is listed as unverified, since holiday and gap cannot be told apart;
- levels: a level that is not positive (NSE published an open of 0 on two days), or a day whose high and low do not
  contain its open and close;
- overlap: the table's close against the India VIX close the repository already holds from NSE's daily index-close
  files (A3/A10, from 2017), day by day over the days both cover. A close that equals the history's close rounded
  half-up to the other file's decimals is listed as `rounded` (the index-close files give two decimals on many days
  from 2017 to February 2025, the history four); any other difference is `differs`.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from ..constants import SESSION_MUHURAT, SESSION_SPECIAL
from ..research_data.calendar import CalendarError, SessionCalendar

GAP_FIELDS = ("date", "kind", "detail")
LEVEL_FIELDS = ("date", "kind", "open", "high", "low", "close")
LEVELS = ("open", "high", "low", "close")
NOT_POSITIVE, OUTSIDE_RANGE = "not_positive", "outside_low_high"
OVERLAP_FIELDS = ("date", "kind", "history_close", "index_close_close")
SESSION_WITHOUT_ROW = "gap", "NSE calendar session with no VIX row"
ROW_ON_CLOSED_DAY = "row_on_closed_day", "a VIX row on a day the NSE calendar calls closed"
MUHURAT_ROW = "muhurat_session", "a VIX row on a one-hour muhurat session, not a regular day"
SPECIAL_ROW = "special_session", "a VIX row on a weekend special session, not a regular day"
UNVERIFIED = "unverified", "weekday without a row; the session calendar does not cover this year"
WEEKEND_ROW = "weekend_row", "a VIX row on a weekend; the session calendar does not cover this year"
CALENDAR_LACKS_YEAR = "calendar_lacks_year", "the session calendar has no rows for this year: add NSE's circular"
SATURDAY = 5
DIFFERS, ROUNDED = "differs", "rounded"
ONLY_HISTORY, ONLY_INDEX_CLOSE = "only_in_history", "only_in_index_close"


def gap_rows(days: set[date], calendar: SessionCalendar, calendar_first: date) -> list[tuple[str, str, str]]:
    """Every day from the table's first to its last day that is a gap, unverified or doubtful. A day the calendar
    cannot answer is `unverified` only before `calendar_first`; later, the calendar lacks a year and that is named."""
    if not days:
        return []
    found, day = [], min(days)
    while day <= max(days):
        kind = _gap_kind(day, day in days, calendar, calendar_first)
        if kind:
            found.append((day.isoformat(), *kind))
        day += timedelta(days=1)
    return found


def _gap_kind(day: date, has_row: bool, calendar: SessionCalendar, calendar_first: date) -> tuple[str, str] | None:
    try:
        kind = calendar.session_kind(day)
    except CalendarError:
        if day >= calendar_first:
            return CALENDAR_LACKS_YEAR
        if day.weekday() < SATURDAY:
            return None if has_row else UNVERIFIED
        return WEEKEND_ROW if has_row else None
    if kind is None:
        return ROW_ON_CLOSED_DAY if has_row else None
    if not has_row:
        return SESSION_WITHOUT_ROW
    return {SESSION_MUHURAT: MUHURAT_ROW, SESSION_SPECIAL: SPECIAL_ROW}.get(kind)


def level_rows(rows: list[dict[str, str]]) -> list[tuple[str, ...]]:
    """Days with a level that is not positive, or whose open or close lies outside their own low-high, as published."""
    found = []
    for r in rows:
        kind = _level_kind(*(float(r[k]) for k in LEVELS))
        if kind:
            found.append((r["date"], kind, *(r[k] for k in LEVELS)))
    return found


def _level_kind(open_: float, high: float, low: float, close: float) -> str | None:
    if min(open_, high, low, close) <= 0:
        return NOT_POSITIVE
    if low <= open_ <= high and low <= close <= high:
        return None
    return OUTSIDE_RANGE


def overlap_rows(history: Mapping[date, str], index_close: Mapping[date, str]) -> list[tuple[str, ...]]:
    """Every day both sources should hold (from the later first day to the earlier last day) where they disagree or
    only one has the day. Closes are compared as numbers (NSE writes 15.8 in one file and 15.80 in another)."""
    if not history or not index_close:
        return []
    start, end = max(min(history), min(index_close)), min(max(history), max(index_close))
    found = []
    for day in sorted(d for d in set(history) | set(index_close) if start <= d <= end):
        ours, theirs = history.get(day, ""), index_close.get(day, "")
        if not ours or not theirs:
            found.append((day.isoformat(), ONLY_INDEX_CLOSE if not ours else ONLY_HISTORY, ours, theirs))
        elif float(ours) != float(theirs):
            found.append((day.isoformat(), ROUNDED if _rounds_to(ours, theirs) else DIFFERS, ours, theirs))
    return found


def _rounds_to(precise: str, rounded: str) -> bool:
    """True when `rounded` is `precise` rounded half-up to `rounded`'s own number of decimals."""
    places = Decimal(rounded).as_tuple().exponent
    return Decimal(precise).quantize(Decimal(1).scaleb(places), rounding=ROUND_HALF_UP) == Decimal(rounded)
