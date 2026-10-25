"""This month, right vs wrong, as a calendar grid (Mon-Fri columns, weeks as rows): each scored trading day a
rounded cell with its date number, coloured by the result with its glyph; closed weekdays grey, the future dashed."""

from __future__ import annotations

from datetime import date, timedelta

from .formats import GLYPH
from .values import Day

WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri")


def month_grid(days: list[Day], issue_day: date) -> str:
    by_date = {d.day: d for d in days}
    first = issue_day.replace(day=1)
    cursor = first - timedelta(days=first.weekday())
    cells = []
    while cursor < first or cursor.month == issue_day.month:
        if cursor.weekday() < 5:
            cells.append(_cell(cursor, by_date.get(cursor), first, issue_day))
        cursor += timedelta(days=1)
    head = "".join(f"<span>{w}</span>" for w in WEEKDAYS)
    return f'<div class="calhead">{head}</div><div class="calgrid">{"".join(cells)}</div>'


def _cell(day: date, scored: Day | None, first: date, issue_day: date) -> str:
    if day < first:
        return '<div class="cal pad"></div>'
    if scored is not None:
        return f'<div class="cal {scored.result}"><b>{day.day}</b><span>{GLYPH[scored.result]}</span></div>'
    return f'<div class="cal {"off" if day <= issue_day else "future"}"><b>{day.day}</b></div>'
