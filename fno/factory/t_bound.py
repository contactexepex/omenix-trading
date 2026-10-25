"""The lower one-sided bound of a measured mean (FACTORY_RULES section 2): Student t with n - 1 degrees of freedom.

The quantile inverts G8's `t_cdf` by bisection (scipy is not installed; no third t table in the repository)."""

from __future__ import annotations

import math

from ..forecast_v4.student_t import t_cdf

_STEPS = 200  # halvings: far below a rupee for any t under 1,000


def t_quantile(probability: float, df: float) -> float:
    """t with P(T <= t) = probability, for probability in (0.5, 1)."""
    if not 0.5 < probability < 1:
        raise ValueError(f"probability must be in (0.5, 1), not {probability!r}")
    low, high = 0.0, 1.0
    while t_cdf(high, df) < probability:
        low, high = high, high * 2
    for _ in range(_STEPS):
        middle = (low + high) / 2
        low, high = (middle, high) if t_cdf(middle, df) < probability else (low, middle)
    return (low + high) / 2


def lower_bound(mean: float, sd: float, n: int, level: float) -> float:
    if n < 2:
        raise ValueError("a measured mean needs at least 2 trades for its bound")
    return mean - t_quantile(level, n - 1) * sd / math.sqrt(n)
