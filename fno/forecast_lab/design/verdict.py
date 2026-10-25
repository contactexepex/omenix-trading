"""The editions' check block (owner, 23 Oct 2026, "Owner on the evening forecast report" in the conversation log):
per index and in this order, the verdict (the close against each range, inside or outside by how many points, glyph
and word, then right or wrong) or, when there is none, a red line first saying what is missing, why and when the
answer comes; the last checked day is then named, never shown as today. Every word is the FL1 builder's (stories
FL1-1e and FL1-1f: `plain.py` and `verdict_words.py`, one source); right = inside "almost certainly"."""

from __future__ import annotations

from html import escape

from ..page.cues import FAILED, NOT_OUT_YET
from ..page.model import IndexView, PageView
from ..page.plain import OFFICIAL, PROVISIONAL, VERDICTS, morning_report
from ..page.verdict_words import cause_lines, day_line, edge_words, no_verdict_words, range_words, size_line
from .blocks import result_card
from .formats import GLYPH, GREEN, RED, WORD, long
from .values import Day

# These three have no text-line twin
NOT_CHECKED = "today: not checked (no verdict)"
NOT_CONFIRMED = "NSE's close; the official file has not confirmed it yet"
LAST_CHECKED = "last checked: {day}, {result}"


def report_of(view: PageView) -> str:
    return morning_report(view.day, view.next_session)


def close_label(d: Day, view: PageView) -> str:
    return PROVISIONAL.format(report=report_of(view)) if d.provisional else OFFICIAL


def check_lines(d: Day, prefix: str, label: str) -> str:
    """The verdict's rows: the close, each range with the forecast's own edges and inside or outside by how many
    points (FL1-1f), then right or wrong by the builder's flag."""
    inside_90 = d.result != RED
    return (
        f'<ul class="check"><li>{escape(prefix)}: closed <b>{d.close:,.2f}</b> ({escape(label)})</li>'
        f"<li>most likely {range_words(d.lo50, d.hi50)} → <b>{escape(edge_words(d.close, d.lo50, d.hi50))}</b></li>"
        f"<li>almost certainly {range_words(d.lo90, d.hi90)} → <b>{escape(edge_words(d.close, d.lo90, d.hi90))}</b>"
        f'</li><li>verdict: <b class="{GREEN if inside_90 else RED}">{VERDICTS[inside_90]}</b></li></ul>'
    )


def unavailable(view: PageView) -> tuple[str, ...]:
    """Why each context source the evening expected has no reading (the text line's rule, `page/message.py`)."""
    return tuple(s.why for s in view.cues if s.status in (NOT_OUT_YET, FAILED) and s.why)


def why_rows(index: IndexView, view: PageView) -> list[str]:
    """The evening's why, each row labelled measured or reasoning by its words: the day's path, its size, a miss's
    measured cause or that there is none, the context (never a cause)."""
    rows = [line for line in (day_line(index), size_line(index)) if line]
    return [escape(line) for line in rows + cause_lines(index, unavailable(view))]


def unchecked_block(index: IndexView, view: PageView, days: list[Day]) -> str:
    """No verdict: the red line first (what is missing, why and when the answer comes, with its own glyph), then
    the last checked day, named as such."""
    why = no_verdict_words(index, view.day, view.next_session) if index.unchecked else f"⚠ {NOT_CHECKED}"
    last = days[-1] if days else None
    result = f"{GLYPH[last.result]} {WORD[last.result]}" if last else ""
    named = f'<p class="line">{LAST_CHECKED.format(day=long(last.day), result=result)}</p>' if last else ""
    return f'<p class="nocheck">{escape(why)}</p>{named}'


def day_word(d: Day, view: PageView) -> str:
    """ "today" only for the page's own day; a past day is always named (orchestrator, 23 Oct)."""
    return "today" if d.day == view.day else long(d.day)


def evening_verdict(index: IndexView, view: PageView, today: Day | None, days: list[Day]) -> str:
    if today is None:
        return unchecked_block(index, view, days)
    return check_lines(today, day_word(today, view), close_label(today, view)) + result_card(today, report_of(view))


def morning_check(index: IndexView, view: PageView, checked: Day | None) -> str:
    """The morning's check of the previous session on NSE's official close, when the model carries one."""
    if checked is None:
        return ""
    label = NOT_CONFIRMED if checked.provisional else OFFICIAL  # judge 538 F4: never "tomorrow" here
    return f'<div class="lab">Last session’s check</div>{check_lines(checked, long(checked.day), label)}'
