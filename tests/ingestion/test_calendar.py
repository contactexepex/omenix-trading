"""NSE session calendar and trading-day logic (``fno/ingestion/research_data/calendar.py`` and
``storage/trading_days.py``), driven by a tiny committed fixture calendar for 2026."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from fno.ingestion.research_data.calendar import (
    CalendarError,
    CsvSessionCalendar,
    load_session_calendar,
)
from fno.ingestion.storage.trading_days import is_trading_day, next_trading_day

FIXTURE = Path(__file__).parent.parent / "fixtures" / "nse_sessions_2026.csv"

HOLIDAY = date(2026, 1, 26)  # Monday, Republic Day (holiday)
SATURDAY_SPECIAL = date(2026, 2, 21)  # weekend special session
MUHURAT = date(2026, 11, 8)  # Sunday muhurat session
NORMAL_WEEKDAY = date(2026, 10, 12)  # Monday, ordinary regular session
PLAIN_WEEKEND = date(2026, 3, 14)  # Saturday, market closed


@pytest.fixture
def calendar() -> CsvSessionCalendar:
    return load_session_calendar(FIXTURE)


def test_session_kinds(calendar: CsvSessionCalendar) -> None:
    assert calendar.session_kind(NORMAL_WEEKDAY) == "regular"
    assert calendar.session_kind(SATURDAY_SPECIAL) == "special"
    assert calendar.session_kind(MUHURAT) == "muhurat"
    assert calendar.session_kind(HOLIDAY) is None  # a holiday is not a session
    assert calendar.session_kind(PLAIN_WEEKEND) is None  # ordinary weekend


def test_is_trading_day(calendar: CsvSessionCalendar) -> None:
    assert is_trading_day(calendar, NORMAL_WEEKDAY) is True
    assert is_trading_day(calendar, SATURDAY_SPECIAL) is True  # a special weekend session trades
    assert is_trading_day(calendar, MUHURAT) is False  # muhurat is a session but not a trading day for these rules
    assert is_trading_day(calendar, HOLIDAY) is False
    assert is_trading_day(calendar, PLAIN_WEEKEND) is False


def test_is_session_vs_trading_day_differ_on_muhurat(calendar: CsvSessionCalendar) -> None:
    assert calendar.is_session(MUHURAT) is True
    assert is_trading_day(calendar, MUHURAT) is False


def test_next_trading_day_steps_over_muhurat(calendar: CsvSessionCalendar) -> None:
    # The day before the Sunday muhurat is Friday 6 Nov; its next trading day skips the muhurat to Monday 9 Nov.
    assert next_trading_day(calendar, date(2026, 11, 6)) == date(2026, 11, 9)


def test_previous_and_next_session_skip_holiday(calendar: CsvSessionCalendar) -> None:
    # 26 Jan is a holiday; the session before 27 Jan is 23 Jan (Fri), after is 27 Jan onwards.
    assert calendar.previous_session(date(2026, 1, 27)) == date(2026, 1, 23)
    assert calendar.next_session(HOLIDAY) == date(2026, 1, 27)


def test_sessions_range_excludes_closed_days(calendar: CsvSessionCalendar) -> None:
    sessions = calendar.sessions(date(2026, 1, 23), date(2026, 1, 27))
    assert HOLIDAY not in sessions
    assert date(2026, 1, 24) not in sessions  # Saturday
    assert date(2026, 1, 23) in sessions and date(2026, 1, 27) in sessions


def test_day_outside_range_raises(calendar: CsvSessionCalendar) -> None:
    with pytest.raises(CalendarError):
        calendar.session_kind(date(2030, 1, 1))


def test_calendar_sha256_is_stable(calendar: CsvSessionCalendar) -> None:
    again = load_session_calendar(FIXTURE)
    assert calendar.calendar_sha256() == again.calendar_sha256()
    assert len(calendar.calendar_sha256()) == 64


def test_bad_rows_rejected() -> None:
    with pytest.raises(CalendarError):  # weekday marked as a weekend special session
        CsvSessionCalendar("date,kind,description,source_url\n2026-10-12,special,x,https://e.org\n")
    with pytest.raises(CalendarError):  # missing https source link
        CsvSessionCalendar("date,kind,description,source_url\n2026-01-26,holiday,x,\n")
