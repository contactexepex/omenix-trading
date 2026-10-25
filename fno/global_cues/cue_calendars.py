"""Which dates a cue's publisher has a value for (story A17b): the calendar behind each reading's expected date.

- `NyseCalendar`: US stock-market sessions (the S&P 500, the Nasdaq 100), from NYSE's holiday rules, computed, and a
  sourced list of unscheduled closures (`research/data/global-cues/us_market_closures.csv`). Reasoning only: rules,
  not NYSE's own list per year; a test checks them against the archived S&P 500 trading dates since 2007.
- `WeekdayCalendar`: Monday to Friday. The US 10-year's simplification: it follows the bond-market (SIFMA) calendar,
  not NYSE's, so a bond holiday reads `behind`, never wrongly `current`.
- `NseSessionCalendar`: the A7 calendar's `regular` and `special` sessions (no muhurat), for USD/INR; Monday to Friday
  before the calendar's first year.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from datetime import date, timedelta

from ..constants import SESSION_MUHURAT
from ..research_data.calendar import SessionCalendar

SATURDAY, SUNDAY, MONDAY, THURSDAY = 5, 6, 0, 3
JUNETEENTH_FROM = 2022  # first year NYSE closed for Juneteenth


class CueCalendar(ABC):
    @abstractmethod
    def is_session(self, day: date) -> bool:
        """Whether the publisher has a value for this date."""


class WeekdayCalendar(CueCalendar):
    def is_session(self, day: date) -> bool:
        return day.weekday() < SATURDAY


class NseSessionCalendar(CueCalendar):
    def __init__(self, calendar: SessionCalendar, first: date):
        self.calendar, self.first = calendar, first

    def is_session(self, day: date) -> bool:
        if day < self.first:
            return day.weekday() < SATURDAY
        kind = self.calendar.session_kind(day)
        return kind is not None and kind != SESSION_MUHURAT

    def next_open(self, day: date) -> date:
        """The first session with a 09:15 open after a date: a muhurat hour has none (the `live` label, story A17b).
        Past the calendar's last year it raises CalendarError, so a label is never guessed."""
        day += timedelta(days=1)
        while not self.is_session(day):
            day += timedelta(days=1)
        return day


class NyseCalendar(CueCalendar):
    def __init__(self, closures: Iterable[date]):
        """`closures`: unscheduled whole-day closures (national days of mourning, storms), each sourced."""
        self.closures = frozenset(closures)
        self._holidays: dict[int, frozenset[date]] = {}

    def is_session(self, day: date) -> bool:
        return day.weekday() < SATURDAY and day not in self.closures and day not in self.holidays(day.year)

    def holidays(self, year: int) -> frozenset[date]:
        if year not in self._holidays:
            self._holidays[year] = frozenset(_nyse_holidays(year))
        return self._holidays[year]


def _nyse_holidays(year: int) -> list[date]:
    fixed = [_observed(date(year, 7, 4)), _observed(date(year, 12, 25))]
    if year >= JUNETEENTH_FROM:
        fixed.append(_observed(date(year, 6, 19)))
    new_year = date(year, 1, 1)
    if new_year.weekday() != SATURDAY:  # NYSE does not close the Friday before a Saturday New Year's Day
        fixed.append(_observed(new_year))
    return fixed + [
        _nth_weekday(year, 1, MONDAY, 3),  # Martin Luther King Jr. Day
        _nth_weekday(year, 2, MONDAY, 3),  # Washington's Birthday
        _easter(year) - timedelta(days=2),  # Good Friday
        _last_weekday(year, 5, MONDAY),  # Memorial Day
        _nth_weekday(year, 9, MONDAY, 1),  # Labor Day
        _nth_weekday(year, 11, THURSDAY, 4),  # Thanksgiving
    ]


def _observed(day: date) -> date:
    """A Saturday holiday is observed on Friday, a Sunday one on Monday."""
    if day.weekday() == SATURDAY:
        return day - timedelta(days=1)
    return day + timedelta(days=1) if day.weekday() == SUNDAY else day


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    first = date(year, month, 1)
    return first + timedelta(days=(weekday - first.weekday()) % 7 + 7 * (n - 1))


def _last_weekday(year: int, month: int, weekday: int) -> date:
    last = date(year + month // 12, month % 12 + 1, 1) - timedelta(days=1)
    return last - timedelta(days=(last.weekday() - weekday) % 7)


def _easter(year: int) -> date:
    """Western Easter Sunday (the anonymous Gregorian algorithm)."""
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l_ = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l_) // 451
    month = (h + l_ - 7 * m + 114) // 31
    return date(year, month, (h + l_ - 7 * m + 114) % 31 + 1)
