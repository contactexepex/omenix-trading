"""The pages' text blocks: a forecast's three big numbers (rounded outward, the morning text's rule), the result card
and the day-by-day table (the forecast's own edges to the point, FL1-1f's rule: a close a few points outside is never
shown inside a rounded range), the counts with percentages and the misses table. Every number is read from the `Day`
values; the blocks compute only shares."""

from __future__ import annotations

from html import escape

from ..page.model import IndexView
from ..page.verdict_words import range_words
from .formats import AMBER, GLYPH, GREEN, RED, WORD, fmt, fmt_mid, fmt_range, signed, signed_pct
from .values import Day, reason_for, today_of

RESULTS = (GREEN, AMBER, RED)
NO_REASON_KEPT = "reason not kept for this day"
PROVISIONAL = "close as read after 15:30; the official file confirms it in {report}"
NEXT_MORNING = "the next morning report"


def big_numbers(index: IndexView, label: str, missing: str) -> str:
    """The three big numbers of a forecast: the morning's for today, the evening's for the next session."""
    n1, n3 = today_of(index, "N1"), today_of(index, "N3")
    if n1 is None:
        return f'<div class="lab first">{label}</div><div class="line">{missing}</div>'
    outlook = f"in 3 days most likely {fmt_range(n3.lo50, n3.hi50)}" if n3 else ""
    return (
        f'<div class="lab first">{label} · close {n1.date}</div><div class="three big">'
        f"<div><small>Most likely</small><b>{fmt_range(n1.lo50, n1.hi50)}</b><span>1 day in 2</span></div>"
        f"<div><small>Almost certainly</small><b>{fmt_range(n1.lo90, n1.hi90)}</b><span>9 days in 10</span></div>"
        f"<div><small>Forecast middle</small><b>{fmt_mid(n1.mid)}</b><span>{outlook}</span></div></div>"
    )


def where_it_closed(d: Day) -> str:
    """One plain line: how far outside which range, and which way."""
    if d.result == GREEN:
        side = "above" if d.close >= d.mid else "below"
        return f"Closed inside “most likely”, {fmt(abs(d.gap))} pts {side} the forecast middle"
    if d.result == AMBER:
        gap = d.close - d.hi50 if d.close > d.hi50 else d.lo50 - d.close
        side = "above" if d.close > d.hi50 else "below"
        return f"Closed {fmt(gap)} pts {side} the most-likely range, inside “almost certainly”"
    gap = d.close - d.hi90 if d.close > d.hi90 else d.lo90 - d.close
    return f"Closed {fmt(gap)} pts {'above' if d.close > d.hi90 else 'below'} “almost certainly”"


def result_card(d: Day, report: str = NEXT_MORNING) -> str:
    """`report`: the morning report that confirms a provisional close (FL1-1e: never "tomorrow" on a Friday)."""
    note = escape(PROVISIONAL.format(report=report)) if d.provisional else d.date_long
    return (
        f'<div class="result"><div class="three">'
        f"<div><small>Forecast middle</small><b>{fmt(d.mid)}</b>"
        f"<span>most likely {range_words(d.lo50, d.hi50)}</span></div>"
        f"<div><small>Actual close</small><b>{fmt(d.close)}</b><span>{note}</span></div>"
        f'<div><small>Gap</small><b class="{d.result}">{signed(d.gap)} pts</b>'
        f"<span>{signed_pct(d.gap_pct)}</span></div>"
        f'</div><div class="verdict"><span class="chip {d.result}">{GLYPH[d.result]} {WORD[d.result]}</span>'
        f'<span class="plainline">{where_it_closed(d)}</span></div></div>'
    )


def day_table(index: IndexView, days: list[Day]) -> str:
    rows = []
    for d in reversed(days):
        sign = "pos" if d.gap >= 0 else "neg"
        reason = escape(reason_for(index, d)) if d.result == RED else ""
        rows.append(
            f"<tr><td>{d.date}</td><td>{fmt(d.mid)}</td><td>{range_words(d.lo50, d.hi50)}</td>"
            f"<td>{range_words(d.lo90, d.hi90)}</td><td><b>{fmt(d.close)}</b></td>"
            f'<td class="{sign}">{signed(d.gap)}</td><td class="{sign}">{signed_pct(d.gap_pct)}</td>'
            f'<td class="{d.result}">{GLYPH[d.result]} {WORD[d.result]}</td><td class="reason">{reason}</td></tr>'
        )
    return (
        '<div class="scroll"><table class="days"><thead><tr><th>Date</th><th>Forecast middle</th><th>Most likely</th>'
        "<th>Almost certainly</th><th>Actual close</th><th>Gap pts</th><th>Gap %</th><th>Result</th>"
        f'<th class="reason">Reason</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>'
    )


def counts_line(days: list[Day], label: str) -> str:
    n = len(days)
    counts = {r: sum(d.result == r for d in days) for r in RESULTS}
    pct = {r: f"{counts[r] / n:.0%}" if n else "–" for r in RESULTS}
    parts = [f'<b class="{r}">{GLYPH[r]} {WORD[r]} {counts[r]} ({pct[r]})</b>' for r in RESULTS]
    return f'<div class="counts">{" · ".join(parts)} <span>of {n} {label}</span></div>'


def misses_table(index: IndexView, days: list[Day]) -> str:
    rows = []
    for d in reversed(days):
        if d.result != RED:
            continue
        reason = escape(reason_for(index, d)) or f"<i>{NO_REASON_KEPT}</i>"
        rows.append(
            f'<tr><td>{d.date}</td><td class="{"pos" if d.gap >= 0 else "neg"}">{signed(d.gap)}</td>'
            f"<td>{reason}</td></tr>"
        )
    body = "".join(rows) or '<tr><td colspan="3">No miss in the last 30 days.</td></tr>'
    return (
        '<table class="misses"><thead><tr><th>Date</th><th>Gap pts</th><th>Reason</th></tr></thead>'
        f"<tbody>{body}</tbody></table>"
    )
