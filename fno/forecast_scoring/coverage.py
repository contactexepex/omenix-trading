"""Each book's live coverage for story G4's report (story G5 criterion 3): the days it has at least one scored-eligible
probability, out of every session day with a v2 pack from the common start to the as-of day. A book missing a day,
or whose day is unscored (late, exposed, model mismatch, a breach), shows lower coverage, never a later start; a day
without a book's records is missing, never zero skill."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date

from ..constants import BOOKS
from .score_inputs import LIVE, ScoredForecast


def book_coverage(
    pack_days: Iterable[date], forecasts: Iterable[ScoredForecast], common_start: date | None, as_of: date
) -> dict[str, dict[str, int]] | None:
    """book -> {"counted_days", "pack_days"}; None before a common start exists."""
    if common_start is None:
        return None
    days = sorted(d for d in set(pack_days) if common_start <= d <= as_of)
    counted = {(f.book, f.day) for f in forecasts if f.mode == LIVE and f.probability is not None}
    return {book: {"counted_days": sum((book, d) in counted for d in days), "pack_days": len(days)} for book in BOOKS}
