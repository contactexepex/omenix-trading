"""Trading-day counting for the cards' session rules (story MS-P1e). The calendar is A7's `TradingDays`
(`fno/research_engine/cycles.py`), which answers `is_trading_day`, `next_after` and `last_on_or_before`; this module
only counts and steps back, which it lacks."""

from datetime import date, timedelta
from typing import Protocol


class TradingCalendar(Protocol):
    def is_trading_day(self, day: date) -> bool: ...

    def next_after(self, day: date) -> date: ...

    def last_on_or_before(self, day: date) -> date: ...


def sessions_between(calendar: TradingCalendar, after: date, through: date) -> int:
    """Trading sessions in (after, through]: 1 on the day before an expiry for `through` = the expiry."""
    return sum(calendar.is_trading_day(after + timedelta(days=n)) for n in range(1, (through - after).days + 1))


def previous_session(calendar: TradingCalendar, day: date) -> date:
    return calendar.last_on_or_before(day - timedelta(days=1))


def nth_session_after(calendar: TradingCalendar, day: date, n: int) -> date:
    for _ in range(n):
        day = calendar.next_after(day)
    return day
