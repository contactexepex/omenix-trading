"""Number words shared by every block: ranges rounded outward to 10 (plain.py's rule, so the text lines and the
pages never disagree), the middle to the nearest 10, signed gaps, and the three-colour result read from the
builder's inside flags (never recomputed from the band)."""

from __future__ import annotations

from datetime import date

from ..page.model import Outcome
from ..page.plain import RESULTS, STEP, outward

GREEN, AMBER, RED = "green", "amber", "red"
FLAGS = {GREEN: (True, True), AMBER: (False, True), RED: (False, False)}  # (inside_50, inside_90) per colour
# One source for the result words: plain.RESULTS carries "✓ Correct", "⚠ Close call", "✗ Missed" (glyph, word)
GLYPH = {colour: RESULTS[flags].split(" ", 1)[0] for colour, flags in FLAGS.items()}
WORD = {colour: RESULTS[flags].split(" ", 1)[1] for colour, flags in FLAGS.items()}
DASH = " – "


def fmt(value: float) -> str:
    return f"{int(round(value)):,}"


def fmt_mid(value: float) -> str:
    return f"{int(round(value / STEP) * STEP):,}"


def fmt_range(low: float, high: float) -> str:
    lo, hi = outward(low, high)
    return f"{lo:,}{DASH}{hi:,}"


def fmt_low(value: float) -> str:
    return f"{outward(value, value)[0]:,}"


def fmt_high(value: float) -> str:
    return f"{outward(value, value)[1]:,}"


def signed(value: float) -> str:
    return f"{'+' if value >= 0 else '−'}{fmt(abs(value))}"


def signed_pct(value: float) -> str:
    return f"{'+' if value >= 0 else '−'}{abs(value):.2f}%"


def status(point: Outcome) -> str:
    """GREEN inside "most likely", AMBER inside "almost certainly" only, RED outside both (owner, 21 Oct 2026)."""
    return GREEN if point.inside_50 else AMBER if point.inside_90 else RED


def short(day: date) -> str:
    return f"{day.day} {day:%b}"


def long(day: date) -> str:
    return f"{day:%a} {day.day} {day:%b}"
