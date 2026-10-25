"""Edition B, about 20:05 IST, "Was today's forecast right?": the key, then per index the owner's top block (23 Oct
2026): the verdict or a red "not checked" line first, why, the record with back-tested apart, the next session's
forecast; then chart 1 (forecast vs close, 30 days), chart 2 (how far off), the day-by-day table, the counts with
percentages and the month calendar, the reliability trend, when it was wrong, and the levels and flows."""

from __future__ import annotations

from ..page.model import IndexView, PageView
from .blocks import big_numbers, counts_line, day_table, misses_table
from .calendar import month_grid
from .formats import GREEN, RED, fmt, long
from .gap_chart import GapChart, GapLayout
from .lines_chart import LinesChart, LinesLayout
from .page import (
    KEY,
    PHONE,
    WIDE,
    both,
    foot,
    head,
    header,
    levels_table,
    method_line,
    record_pill,
    trend,
    why_block,
)
from .trend_chart import trend_state
from .values import Day, days_of, result_of, rolling_90
from .verdict import day_word, evening_verdict, why_rows

TITLE, ISSUED = "Was today’s forecast right?", "20:05"
GRID = {"NIFTY": 100, "BANKNIFTY": 250}
DEFAULT_GRID = 100
SHOWN, TABLE_ROWS = 30, 10
WHY_TITLE = {GREEN: "Why it was correct", "amber": "Why a close call", RED: "Why it missed"}
NEXT = "Next session’s forecast"
NO_FORECAST = "no forecast sealed for the next session"
NOT_CHECKED = "today: not checked"
KEY_LINES = (
    '<p class="key"><span><i class="ln mid"></i>forecast middle</span><span><i class="ln close"></i>actual '
    'close</span><span class="nowrap"><i class="dot green"></i>✓ correct · <i class="dot amber"></i>⚠ close '
    'call · <i class="dot red"></i>✗ missed</span></p>'
)
KEY_GAP = (
    '<p class="key"><span><i class="ln r50"></i>most likely edges</span><span><i class="ln r90"></i>almost '
    'certainly edges</span><span class="nowrap"><i class="dot green"></i>✓ · <i class="dot amber"></i>⚠ · '
    '<i class="dot red"></i>✗</span></p>'
)


def charts(name: str, days: list[Day], grid: int) -> tuple[str, str]:
    a1 = f"{name}: forecast middle and actual close, last {len(days)} days"
    a2 = f"{name}: how far the close was from the forecast middle, last {len(days)} days"
    c1 = both(
        LinesChart(days, LinesLayout(WIDE, grid), date_every=3).svg(a1),
        LinesChart(days, LinesLayout(PHONE, grid, plot_height=200, axis_width=46), date_every=7).svg(a1),
    )
    c2 = both(
        GapChart(days, GapLayout(WIDE, grid), date_every=3).svg(a2),
        GapChart(days, GapLayout(PHONE, grid, plot_height=200, axis_width=46), date_every=7).svg(a2),
    )
    return c1, c2


def this_month(days: list[Day], view: PageView) -> list[Day]:
    return [d for d in days if (d.day.year, d.day.month) == (view.day.year, view.day.month)]


def backtested_note(index: IndexView) -> str:
    tested = getattr(index, "backtested", 0)
    return (
        f'<p class="note">{tested} of the last {index.scored} were scored on a back-fill, not live</p>'
        if tested
        else ""
    )


def top_block(index: IndexView, view: PageView, today: Day | None, days: list[Day]) -> str:
    """The owner's order (23 Oct): verdict or the red line, why, the record, then the next session's forecast."""
    closed = f"{day_word(today, view)} · closed {fmt(today.close)}" if today else NOT_CHECKED
    why = why_block(WHY_TITLE[today.result], why_rows(index, view), index, with_cues=False) if today else ""
    return (
        f'<div class="card"><h2>{index.underlying}<small>{closed}</small></h2>'
        f"{evening_verdict(index, view, today, days)}{why}"
        f'<div class="record">{record_pill(index)}</div>{method_line(index)}'
        f"{big_numbers(index, NEXT, NO_FORECAST)}</div>"
    )


def section(index: IndexView, view: PageView) -> str:
    name, days = index.underlying, days_of(index, SHOWN)
    if not days:
        return f'<div class="card"><h2>{name}</h2><p class="line">no scored session yet</p></div>'
    today, grid = result_of(index), GRID.get(name, DEFAULT_GRID)
    c1, c2 = charts(name, days, grid)
    state = trend_state(rolling_90(index))
    trend_svg = both(trend(index, days, WIDE).svg(f"{name}: reliability trend"),
                     trend(index, days, PHONE).svg(f"{name}: reliability trend"))  # fmt: skip
    return (
        top_block(index, view, today, days)
        + f'<div class="card"><div class="lab first">{name} · chart 1 · forecast vs actual close, last {len(days)} '
        f'days <span class="when">gridlines every {grid}</span></div>{c1}{KEY_LINES}</div>'
        f'<div class="card"><div class="lab first">{name} · chart 2 · how far off, last {len(days)} days '
        f'<span class="when">actual close minus the forecast middle, in points · above zero = closed higher than '
        f"forecast · dashed = the range edges</span></div>{c2}{KEY_GAP}</div>"
        f'<div class="card"><div class="lab first">{name} · day by day, last {TABLE_ROWS} sessions</div>'
        f"{day_table(index, days[-TABLE_ROWS:])}</div>"
        f'<div class="card"><div class="lab first">{name} · right vs wrong</div>'
        f"{counts_line(days, f'trading days, the last {len(days)}')}"
        f"{counts_line(this_month(days, view), f'trading days in {view.day:%B}')}"
        f"{backtested_note(index)}{month_grid(days, view.day)}</div>"
        f'<div class="card"><div class="lab first">{name} · reliability trend <span class="when">20-day share inside '
        f"“almost certainly” · {state}</span></div>{trend_svg}</div>"
        f'<div class="card"><div class="lab first">{name} · when it was wrong, last {len(days)} days</div>'
        f'{misses_table(index, days)}<div class="lab">Levels and flows · today’s chain and NSE flows</div>'
        f"{levels_table(index)}</div>"
    )


def render_evening(view: PageView) -> str:
    day = long(view.day)
    body = "".join(section(index, view) for index in view.indices)
    return head(f"Evening check, {day}") + header(TITLE, day, ISSUED, view) + KEY + body + foot(view)
