"""The forecast scores of protocol section 7 (story G4): Brier, clipped log score and the calibration table.

Brier `(p - o)^2`, lower is better. Log score `-ln(p')` if `o = 1`, `-ln(1 - p')` if `o = 0`, with
`p' = min(max(p, 0.01), 0.99)`. Calibration: 10 bins `[0, 0.1)`, ..., `[0.8, 0.9)`, `[0.9, 1.0]`; per bin the count,
the mean forecast and the observed frequency. Inputs are probabilities in [0, 1] and outcomes True (1) or False (0).
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

LOG_CLIP = 0.01  # log score: p clipped to [0.01, 0.99]
CALIBRATION_BINS = 10


def brier(p: float, outcome: bool) -> float:
    return (p - float(outcome)) ** 2


def log_score(p: float, outcome: bool) -> float:
    clipped = min(max(p, LOG_CLIP), 1 - LOG_CLIP)
    return -math.log(clipped if outcome else 1 - clipped)


def calibration_bin(p: float) -> int:
    """0 for [0, 0.1), ..., 9 for [0.9, 1.0] (1.0 falls in the last bin)."""
    return min(int(p * CALIBRATION_BINS), CALIBRATION_BINS - 1)


@dataclass(frozen=True)
class CalibrationBin:
    low: float
    high: float
    count: int
    mean_forecast: float | None
    observed_frequency: float | None


def calibration_table(pairs: Sequence[tuple[float, bool]]) -> tuple[CalibrationBin, ...]:
    bins: list[list[tuple[float, bool]]] = [[] for _ in range(CALIBRATION_BINS)]
    for p, outcome in pairs:
        bins[calibration_bin(p)].append((p, outcome))
    return tuple(
        CalibrationBin(
            i / CALIBRATION_BINS,
            (i + 1) / CALIBRATION_BINS,
            len(members),
            sum(p for p, _ in members) / len(members) if members else None,
            sum(o for _, o in members) / len(members) if members else None,
        )  # fmt: skip
        for i, members in enumerate(bins)
    )


@dataclass(frozen=True)
class ScoreSummary:
    """One forecaster's scores on one question (protocol section 7)."""

    scored: int
    mean_brier: float | None
    mean_log_score: float | None
    calibration: tuple[CalibrationBin, ...]


def summarise(pairs: Sequence[tuple[float, bool]]) -> ScoreSummary:
    n = len(pairs)
    return ScoreSummary(
        n,
        sum(brier(p, o) for p, o in pairs) / n if n else None,
        sum(log_score(p, o) for p, o in pairs) / n if n else None,
        calibration_table(pairs),
    )
