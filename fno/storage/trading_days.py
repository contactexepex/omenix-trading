"""Trading days of NSE's session calendar for daily rule files (story A20a): regular and special sessions; a
muhurat-only evening is a session but not a day these rules are set for."""

from __future__ import annotations

from datetime import date

from ..research_data.calendar import SessionCalendar

TRADING_KINDS = ("regular", "special")


def is_trading_day(calendar: SessionCalendar, day: date) -> bool:
    return calendar.session_kind(day) in TRADING_KINDS


def next_trading_day(calendar: SessionCalendar, day: date) -> date:
    """The first trading day after `day`, stepping over a muhurat-only session."""
    following = calendar.next_session(day)
    return following if is_trading_day(calendar, following) else next_trading_day(calendar, following)
