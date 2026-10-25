"""A cue's move against its own recent moves (story FL1-1d-2): the key points rank context by this, so a 1% move in a
quiet cue outranks a 1% move in a jumpy one. Plain arithmetic, stated: |change| over the standard deviation of the
cue's last 60 changes; None with fewer than 20 changes (too few to say what is usual)."""

from __future__ import annotations

import statistics
from collections.abc import Sequence

SPREAD_CHANGES, MIN_CHANGES = 60, 20


def changes(values: Sequence[float], percent: bool) -> list[float]:
    """Each value's change from the one before: in percent for a level, in its own units for a yield."""
    pairs = zip(values, values[1:], strict=False)
    return [(b / a - 1) * 100 if percent else b - a for a, b in pairs if not percent or a]


def size(change: float | None, history: Sequence[float]) -> float | None:
    usual = history[-SPREAD_CHANGES:]
    if change is None or len(usual) < MIN_CHANGES:
        return None
    spread = statistics.pstdev(usual)
    return round(abs(change) / spread, 2) if spread else None
