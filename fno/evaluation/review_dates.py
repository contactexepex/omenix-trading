"""S1's scheduled book reviews (`review_dates`, story F9a): the last NSE session of the sixth full calendar month after
the common start, then of every third calendar month after that. Only this rule is coded; the weekly post-mortem and
the stop-rule review (REPLAN section 4) have their own dates. The first full month is the one after the common start's
month (common start 2 Dec 2026: the first review is on June 2027's last session)."""

from __future__ import annotations

import calendar as month_days
from collections.abc import Callable, Sequence
from datetime import date

FIRST_REVIEW_MONTHS = 6  # full calendar months after the common start
REVIEW_EVERY_MONTHS = 3

SessionsBetween = Callable[[date, date], Sequence[date]]  # the sessions from the first day to the last, both included


def _month_after(year: int, month: int, months: int) -> tuple[int, int]:
    index = year * 12 + month - 1 + months
    return index // 12, index % 12 + 1


def last_session(sessions: SessionsBetween, year: int, month: int) -> date | None:
    found = sessions(date(year, month, 1), date(year, month, month_days.monthrange(year, month)[1]))
    return found[-1] if found else None


def review_dates(common_start: date, sessions: SessionsBetween, through: date) -> list[date]:
    """Every scheduled review on or before `through`."""
    found = []
    year, month = _month_after(common_start.year, common_start.month, FIRST_REVIEW_MONTHS)
    while date(year, month, 1) <= through:
        day = last_session(sessions, year, month)
        if day is not None and day <= through:
            found.append(day)
        year, month = _month_after(year, month, REVIEW_EVERY_MONTHS)
    return found
