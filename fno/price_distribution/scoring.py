"""The quantile score and calibration of G13's forecasts (section 6), in log-return units. Twice the mean pinball loss
over a grid of levels approximates the CRPS (Gneiting and Raftery 2007); seven levels is a coarse grid, said in every
report. Descriptive only: no claim, no family, no Holm."""

from __future__ import annotations

from collections.abc import Sequence


def pinball(level: float, outcome: float, quantile: float) -> float:
    """`max(tau u, (tau - 1) u)` with `u = outcome - quantile`."""
    u = outcome - quantile
    return max(level * u, (level - 1) * u)


def quantile_score(levels: Sequence[float], outcome: float, quantiles: Sequence[float]) -> float:
    """`(2 / L) x sum of the pinball losses` over the L levels."""
    return 2 / len(levels) * sum(pinball(t, outcome, q) for t, q in zip(levels, quantiles, strict=True))


def share_below(outcomes: Sequence[float], quantiles: Sequence[float]) -> float | None:
    """The share of outcomes strictly below their quantile (calibration: near the level when calibrated)."""
    if not outcomes:
        return None
    return sum(1 for y, q in zip(outcomes, quantiles, strict=True) if y < q) / len(outcomes)


def share_inside(outcomes: Sequence[float], lows: Sequence[float], highs: Sequence[float]) -> float | None:
    """The share of outcomes inside `[low, high]` (central-interval coverage)."""
    if not outcomes:
        return None
    return sum(1 for y, lo, hi in zip(outcomes, lows, highs, strict=True) if lo <= y <= hi) / len(outcomes)
