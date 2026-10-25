"""The post-mortem's week (story LR1): the A7 regular sessions from Monday to Friday of the week that ends on a
Saturday. Muhurat and special sessions are never scored (protocol v4), so they are not in the week either."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from ..forecast_v4.sessions import is_scored_session
from ..research_data.calendar import SessionCalendar

SATURDAY = 5  # date.weekday()


class NotSaturday(ValueError):
    """A post-mortem week is named by its Saturday."""


@dataclass(frozen=True)
class Week:
    saturday: date
    sessions: tuple[date, ...]

    @property
    def previous_saturday(self) -> date:
        return self.saturday - timedelta(7)


def latest_saturday(today: date) -> date:
    return today - timedelta((today.weekday() - SATURDAY) % 7)


def build_week(calendar: SessionCalendar, saturday: date) -> Week:
    if saturday.weekday() != SATURDAY:
        raise NotSaturday(f"{saturday} is not a Saturday")
    days = (saturday - timedelta(n) for n in range(5, 0, -1))
    return Week(saturday, tuple(d for d in days if is_scored_session(calendar, d)))
