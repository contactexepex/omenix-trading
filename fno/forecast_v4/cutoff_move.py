"""The "moved after cutoff" flag of protocol v4 (story G10, section 1.6; owner, 15 Oct 2026: flag, never block).

A day whose NIFTY level moved more than X between the 14:30 and the 15:15 marks is flagged and reported apart; nothing
is dropped. The move is `abs(ln(S_15:15 / S_14:30))` on A16's checked levels (live: A16's marks; history: A16b's
checked 15-minute closes, the same level rule). X is the nearest-rank 95th percentile of the 2020-26 history, frozen
with its sample count and source revision (`tools/v4_moved_after_cutoff.py`). History's 5% does not promise 5% of
future days."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from datetime import time

from .terms import V4_CAPTURE_START, V4_COMMON_SNAPSHOT

FLAG_QUANTILE = 0.95
MOVED, NOT_MOVED, NOT_COMPUTABLE = "yes", "no", ""  # the flag as A16's rv row stores it
UP, DOWN, FLAT = "+", "-", "0"  # the move's sign; never a level (raw prices stay in Drive)


def cutoff_move(level_at_capture_start: float, level_at_common_snapshot: float) -> float:
    if level_at_capture_start <= 0 or level_at_common_snapshot <= 0:
        raise ValueError("index levels must be positive")
    return abs(math.log(level_at_common_snapshot / level_at_capture_start))


def nearest_rank(values: Sequence[float], quantile: float = FLAG_QUANTILE) -> float:
    """The ceil(quantile x n)-th smallest value (nearest rank, no interpolation)."""
    if not values:
        raise ValueError("no values")
    return sorted(values)[math.ceil(quantile * len(values)) - 1]


def moved_after_cutoff(move: float, x: float) -> bool:
    """Strictly above X: a move exactly at X is not flagged."""
    return move > x


def cutoff_flag(levels: Mapping[time, float | None], x: float) -> tuple[str, str]:
    """(flag, sign) as A16's 15:30 run records them from its usable levels by mark; both empty when the 14:30 or the
    15:15 level is missing."""
    start, end = levels.get(V4_CAPTURE_START), levels.get(V4_COMMON_SNAPSHOT)
    if start is None or end is None:
        return NOT_COMPUTABLE, NOT_COMPUTABLE
    moved = moved_after_cutoff(cutoff_move(start, end), x)
    change = end - start
    return MOVED if moved else NOT_MOVED, UP if change > 0 else DOWN if change < 0 else FLAT
