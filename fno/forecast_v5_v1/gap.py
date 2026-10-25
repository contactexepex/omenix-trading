"""The measure-gap table (story G14, "The measure gap"; amendment 1 section 5): one row per session that has both an
ok candle row and an ok live row. The pairs and their ratio (candle / live) are G7b's `paired_rv`, the one pairing W8's
drift line and review trigger read too, so the two can never disagree; this module only prints them. W8's review
alert is G7b's."""

from __future__ import annotations

from collections.abc import Sequence

from ..forecast_v4_rules.candle_history import PairedRv
from .records import INPUT_MEASURE

HEADER = ("| Session | Live quote RV | Candle RV (15m bars) | Candle / live |", "|---|---|---|---|")
NO_PAIRS = "no session has both an ok candle row and an ok live row yet"


def gap_table(pairs: Sequence[PairedRv]) -> list[str]:
    """The labelled table, in `paired_rv`'s session order."""
    lines = [f"Measure gap: {INPUT_MEASURE}"]
    if not pairs:
        return [*lines, NO_PAIRS]
    rows = [f"| {p.day:%d %b %Y} | {p.live:.6e} | {p.candle:.6e} | {p.ratio:.3f} |" for p in pairs]
    return [*lines, *HEADER, *rows]
