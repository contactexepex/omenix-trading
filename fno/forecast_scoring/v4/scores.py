"""Per-forecaster scores of protocol v4 section 4 (story G8), all descriptive. Point questions: mean ranking QLIKE,
mean textbook QLIKE on RV > 0, mean squared error on variance and Mincer-Zarnowitz `RV = a + b f`. Probability
questions: mean Brier, mean log score (clipped as G1), G4's 10-bin reliability table, calibration slope and intercept
(the same least squares, outcome on probability) and the Brier skill score against the base rate."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from ...forecast_v4.loss import brier, ranking_qlike, textbook_qlike
from ..scores import CalibrationBin, calibration_table, log_score


@dataclass(frozen=True)
class PointScores:
    n: int
    mean_qlike: float
    mean_textbook_qlike: float | None  # RV > 0 days only
    mean_squared_error: float
    intercept: float | None  # Mincer-Zarnowitz a; None with fewer than 2 distinct forecasts
    slope: float | None


@dataclass(frozen=True)
class ProbabilityScores:
    n: int
    mean_brier: float
    mean_log_score: float
    calibration: tuple[CalibrationBin, ...]
    intercept: float | None
    slope: float | None
    brier_skill: float | None  # 1 - Brier / base rate's Brier on the days both exist; None without them
    skill_n: int  # the paired days the skill score uses (both forecasts and a resolved outcome); n is this
    # forecaster's own scored days, so two forecasters' n can differ while their skill shares the same days


def least_squares(x: Sequence[float], y: Sequence[float]) -> tuple[float | None, float | None]:
    """(a, b) of y = a + b x; (None, None) when x has no spread."""
    n = len(x)
    mean_x, mean_y = math.fsum(x) / n, math.fsum(y) / n
    spread = math.fsum((v - mean_x) ** 2 for v in x)
    if spread == 0:
        return None, None
    slope = math.fsum((u - mean_x) * (v - mean_y) for u, v in zip(x, y, strict=True)) / spread
    return mean_y - slope * mean_x, slope


def point_scores(pairs: Sequence[tuple[float, float]]) -> PointScores | None:
    """`pairs`: (forecast variance, realised variance) on the scored days."""
    if not pairs:
        return None
    forecasts, realised = [f for f, _ in pairs], [rv for _, rv in pairs]
    positive = [textbook_qlike(f, rv) for f, rv in pairs if rv > 0]
    return PointScores(
        len(pairs),
        _mean([ranking_qlike(f, rv) for f, rv in pairs]),
        _mean(positive) if positive else None,
        _mean([(f - rv) ** 2 for f, rv in pairs]),
        *least_squares(forecasts, realised),
    )


def probability_scores(pairs: Sequence[tuple[float, bool]], base_pairs: Sequence[tuple[float, float, bool]]):
    """`pairs`: (probability, outcome) on the scored days; `base_pairs`: (probability, base rate, outcome) on the
    days both exist, for the skill score."""
    if not pairs:
        return None
    base = _mean([brier(b, o) for _, b, o in base_pairs]) if base_pairs else 0.0
    skill = 1 - _mean([brier(p, o) for p, _, o in base_pairs]) / base if base > 0 else None
    return ProbabilityScores(
        len(pairs),
        _mean([brier(p, o) for p, o in pairs]),
        _mean([log_score(p, o) for p, o in pairs]),
        calibration_table(pairs),
        *least_squares([p for p, _ in pairs], [float(o) for _, o in pairs]),
        skill,
        len(base_pairs),
    )


def _mean(values: Sequence[float]) -> float:
    return math.fsum(values) / len(values)
