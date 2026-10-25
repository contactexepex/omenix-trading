"""The evening's top block per index, readable in 30 seconds (owner, 23 Oct 2026; story FL1-1f), in this order:
1. the verdict: today's close against each range, inside or outside by how many points (glyph and word, never colour
   alone), then right or wrong; with no verdict, a first line saying exactly what is missing, why and when the
   answer comes (never only in the footer);
2. why, two or three lines, each labelled measured or reasoning: the day's path against the forecast's centre and
   width; the day's swing against the "most likely" width, and how close a hit came to its edge; on a miss its
   measured reasons, or "no measured cause in our data" (never a guessed cause); the context cues, never a cause;
3. the record, live and back-tested apart.
The verdict shows the forecast's own edges to the point (the morning's words round them outward to 10), so a close a
few points outside an edge is never shown inside a rounded range."""

from __future__ import annotations

from datetime import date

from .cues import CONTEXT, Cue
from .keypoints import QUIET, REASON
from .model import CLOSE_NOT_READ, NO_FORECAST_TODAY, IndexView
from .plain import OFFICIAL, PROVISIONAL, VERDICTS, day_short, light_words, morning_report, record_words
from .reasons import NO_REASON

NARROW = 0.25  # a hit within a quarter of the "almost certainly" half-width of its edge is narrow (reasoning only)
NO_VERDICT = {  # (glyph, sentence): the page prints "<glyph> <sentence>", Slack puts the index in bold between them
    CLOSE_NOT_READ: ("⚠️", "today: no verdict. Today's close could not be read ({why}). The result comes in {report}."),
    NO_FORECAST_TODAY: (
        "❌",
        "today: no verdict. No forecast was issued for today ({why}), so there is nothing to check.",
    ),
}
NO_CAUSE = "Missed (reasoning): no measured cause in our data, so likely noise."
QUIET_CONTEXT = f"Context (measured): {QUIET}."


def edge_words(close: float, low: float, high: float) -> str:
    if low <= close <= high:
        return "✅ inside"
    side, gap = ("below", low - close) if close < low else ("above", close - high)
    return f"❌ outside by {gap:,.2f} points ({side})"


def range_words(low: float, high: float) -> str:
    return f"{low:,.0f}–{high:,.0f}"


def verdict_line(index: IndexView, today: date, next_session: date | None) -> str:
    r, b = index.result, index.result.band
    label = PROVISIONAL.format(report=morning_report(today, next_session)) if r.provisional else OFFICIAL
    when = "today" if r.day == today else day_short(r.day)
    return (f"*{index.underlying}* {when}: closed {r.close:,.2f} ({label}) | most likely {range_words(b.q25, b.q75)} → "
            f"{edge_words(r.close, b.q25, b.q75)} | almost certainly {range_words(b.q05, b.q95)} → "
            f"{edge_words(r.close, b.q05, b.q95)} → {VERDICTS[r.inside_90]}")  # fmt: skip


def _no_verdict(index: IndexView, today: date, next_session: date | None) -> tuple[str, str]:
    glyph, sentence = NO_VERDICT[index.unchecked]
    return glyph, sentence.format(why=index.unchecked_why, report=morning_report(today, next_session))


def no_verdict_words(index: IndexView, today: date, next_session: date | None) -> str:
    """The no-verdict sentence with its glyph, without the index's name (the page's red line)."""
    return " ".join(_no_verdict(index, today, next_session))


def no_verdict_line(index: IndexView, today: date, next_session: date | None) -> str:
    glyph, sentence = _no_verdict(index, today, next_session)
    return f"{glyph} *{index.underlying}* {sentence}"


def day_line(index: IndexView) -> str | None:
    s, b = index.shape, index.result.band
    if s is None:
        return None
    parts = []
    if s.open is not None:
        gap = f" ({s.open - s.previous_close:+,.0f} on the previous close)" if s.previous_close else ""
        parts.append(f"opened {s.open:,.0f}{gap}")
    if s.high is not None and s.low is not None:
        parts.append(f"ranged {range_words(s.low, s.high)}")
    parts.append(f"closed {index.result.close:,.0f}")
    return (f"Day (measured): {', '.join(parts)}; the forecast's centre was {b.q50:,.0f} and its “most likely” width "
            f"{b.q75 - b.q25:,.0f} points.")  # fmt: skip


def _swing(index: IndexView) -> str:
    s, b = index.shape, index.result.band
    if s is None or s.high is None or s.low is None or b.q75 <= b.q25:
        return ""
    ratio = (s.high - s.low) / (b.q75 - b.q25)
    return f"swing {s.high - s.low:,.0f} points = {ratio:.1f}× the “most likely” width"


def size_line(index: IndexView) -> str | None:
    r, b, swing = index.result, index.result.band, _swing(index)
    if not r.inside_90:
        return f"Size (measured): {swing}." if swing else None
    room, half = min(r.close - b.q05, b.q95 - r.close), (b.q95 - b.q05) / 2
    kind = "narrow" if room < NARROW * half else "comfortable"
    edge = f"close {room:,.0f} points inside the nearest “almost certainly” edge, {kind}"
    return (
        f"Size (measured): {'; '.join(x for x in (swing, edge) if x)} (narrow = within ¼ of the half-width; reasoning)."
    )


def _cue(cue: Cue) -> str:
    return cue.text if cue.text is not None else f"{cue.name} {cue.change:+.2f}{cue.unit}"


def cause_lines(index: IndexView, unavailable: tuple[str, ...] = ()) -> list[str]:
    """A miss's measured reasons (or that there is none), then the context: its measured values, "no notable moves",
    or "not available" with each source's reason; never a placeholder."""
    said = [c.text for c in index.why if c.name == REASON and c.text != NO_REASON]
    context = [_cue(c) for c in index.why if c.role == CONTEXT and c.name not in (REASON, QUIET)
               and (c.text is not None or c.change is not None)]  # fmt: skip
    lines = []
    if not index.result.inside_90:
        lines.append(f"Missed because (measured): {'; '.join(said)}." if said else NO_CAUSE)
    if context:
        lines.append(f"Context (measured, not a cause): {', '.join(context)}.")
    elif unavailable:
        lines.append(f"Context: not available ({'; '.join(unavailable)}).")
    else:
        lines.append(QUIET_CONTEXT)
    return lines


def top_block(index: IndexView, today: date, next_session: date | None,
              unavailable: tuple[str, ...] = ()) -> list[str]:  # fmt: skip
    """The index's verdict (or why there is none), its why lines and its record, in that order. `unavailable`: why
    each context source the evening expected has no reading (its "not out yet" or "not read" words)."""
    if index.result is None:
        lines = [no_verdict_line(index, today, next_session)] if index.unchecked else [f"*{index.underlying}*"]
    else:
        why = (line for line in (day_line(index), size_line(index)) if line)
        lines = [verdict_line(index, today, next_session), *why, *cause_lines(index, unavailable)]
    return [*lines, f"{light_words(index)} {record_words(index)}"]
