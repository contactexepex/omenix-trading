"""What both editions share: the page frame (head, header, footer), the key, the cues strip, the reasons block,
the levels table and the reliability chip. The strip, the reasons and the levels read the builder's `Cue` values
when the model carries them (FL1-1d-2) and say "not available yet" in plain words until then."""

from __future__ import annotations

from html import escape
from pathlib import Path

from ..page.model import IndexView, PageView
from ..page.plain import LIGHT_WORDS, RESEARCH, light, record_words
from .trend_chart import TrendChart, TrendLayout
from .values import Day, rolling_90

CSS = Path(__file__).with_name("design.css")
WIDE, PHONE = 1060, 338  # one chart per row: the card's inner width on desktop and on a 390 px phone
BRAND = "Omenix F&amp;O"
NORMAL = "All systems normal"
NOT_AVAILABLE = "not available yet"
CONTEXT = "context, not cause, until a cue feeds the forecaster"
STATUS_WORDS = {"not_out_yet": "not out yet", "not_available": "not available", "failed": "not read"}
KEY = (
    '<div class="card howto"><b>How to read the result.</b> ✓ Correct = closed inside “most likely” (1 day in 2). '
    "⚠ Close call = outside “most likely” but inside “almost certainly” (9 days in 10). ✗ Missed = outside "
    "“almost certainly”. The gap says how far and which way: + closed higher than the forecast middle, − lower.</div>"
)
CHIP_NOTE = "steady = the 20-day share inside “almost certainly” holds 80% or more; watch = it does not"


def head(title: str) -> str:
    return (
        f'<!doctype html><html lang="en"><head><meta charset="utf-8">'
        f'<meta name="viewport" content="width=device-width, initial-scale=1"><title>{escape(title)}</title>'
        f'<style>{CSS.read_text(encoding="utf-8")}</style></head><body><div class="wrap">'
    )


def header(edition: str, day: str, issued: str, view: PageView) -> str:
    return (
        f'<header><div><h1>{BRAND} · {edition}</h1><div class="sub">{day} · issued {issued} IST · '
        f'paper research</div></div><span class="tag">{escape(view.provenance)}</span></header>'
    )


def foot(view: PageView) -> str:
    system = " ".join(f'<b class="bad">⚠ {escape(s)}</b>' for s in view.system) if view.system else f"<b>✓ {NORMAL}</b>"
    return f'<p class="foot">{system} · {RESEARCH}</p></div></body></html>'


def both(desk: str, phone: str) -> str:
    """The desktop drawing and the phone drawing of one chart; CSS shows one of them."""
    return f'<div class="desk">{desk}</div><div class="phone">{phone}</div>'


def _cue_words(cue) -> str:
    """A cue's value with its unit and change; a cue with no value prints its text (a flag, a reason)."""
    if getattr(cue, "value", None) is None:
        return escape(str(getattr(cue, "text", "") or ""))
    unit = escape(str(getattr(cue, "unit", "") or ""))  # the change's unit (Cue.change), never the level's
    value = f"{cue.value:,.2f}".rstrip("0").rstrip(".") if isinstance(cue.value, float) else str(cue.value)
    change = getattr(cue, "change", None)
    tail = (
        f" {'+' if change >= 0 else '−'}{abs(change):,.2f}".rstrip("0").rstrip(".") + unit if change is not None else ""
    )
    return f"{escape(value)}{tail}"


def cues_strip(view: PageView) -> str:
    sections = getattr(view, "cues", ())
    cells = []
    for section in sections:
        status = STATUS_WORDS.get(section.status)
        if status:
            why = escape(str(getattr(section, "why", "") or ""))
            cells.append(
                f'<div class="cell"><small>{escape(section.name)}</small><b>{status}</b><span>{why}</span></div>'
            )
            continue
        for cue in section.items:
            cells.append(
                f'<div class="cell"><small>{escape(cue.name)}</small><b>{_cue_words(cue)}</b>'
                f"<span>{escape(str(cue.as_of))}</span></div>"
            )
    body = "".join(cells) or f'<div class="cell"><b>{NOT_AVAILABLE}</b></div>'
    return (
        f'<div class="card strip"><div class="lab first">Global cues · overnight <span class="when">{CONTEXT}'
        f'</span></div><div class="cells">{body}</div></div>'
    )


def why_block(title: str, lines: list[str], index: IndexView, with_cues: bool = True) -> str:
    """`with_cues`: list the builder's `why` cues after `lines` (the morning); the evening's rows carry them."""
    cues = [
        f"{escape(c.text or c.name)}" + (f": {_cue_words(c)}" if not c.text else "") + f" ({c.role})"
        for c in (getattr(index, "why", ()) if with_cues else ())
    ]
    items = "".join(f"<li>{line}</li>" for line in lines + cues) or f"<li>{NOT_AVAILABLE}</li>"
    return f'<div class="lab">{title} <span class="when">{CONTEXT}</span></div><ul class="why-list">{items}</ul>'


def levels_table(index: IndexView) -> str:
    rows = "".join(
        f"<tr><td>{escape(c.name)}</td><td>{_cue_words(c)} <small>{escape(str(c.as_of))}</small></td></tr>"
        for c in getattr(index, "levels", ())
    )
    body = rows or f"<tr><td>{NOT_AVAILABLE}</td><td></td></tr>"
    return f'<table class="levels"><tbody>{body}</tbody></table>'


def method_line(index: IndexView) -> str:
    """One small line naming the method (judge 434.1): the best on its own history, not proven live."""
    tested = getattr(index, "backtested", 0)
    back = f" · back-tested {tested} of the last {index.scored} days" if tested else ""
    return (
        f'<p class="note">Method: {escape(index.method)}, lowest error on its own history, '
        f"{index.live_days} of {index.days_needed} live days scored{back}</p>"
    )


def trend(index: IndexView, days: list[Day], width: int) -> TrendChart:
    values = rolling_90(index)
    shown = days[-len(values) :] if values else days
    return TrendChart([d.date for d in shown], values, TrendLayout(width))


def record_pill(index: IndexView) -> str:
    """The record in the text line's words (plain.record_words: live and back-tested apart), coloured by the light,
    which the builder rates on live checks only; "too few live days to rate" until it can."""
    state = light(index)
    head = f"{escape(LIGHT_WORDS[state])} · " if state == "none" else ""
    return f'<span class="pill {state}"><i></i>{head}{escape(record_words(index))}</span>'
