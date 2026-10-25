"""Student's t distribution function, standard library only (numpy has none and scipy is not a dependency): the
regularized incomplete beta by its continued fraction (Numerical Recipes 6.4), `P(T <= t) = 1 - I_x(df/2, 1/2) / 2`
for t > 0 with `x = df / (df + t^2)`."""

from __future__ import annotations

import math

MAX_TERMS, TOLERANCE, TINY = 300, 3e-16, 1e-300


def t_cdf(t: float, df: float) -> float:
    if df <= 0:
        raise ValueError(f"degrees of freedom must be > 0, not {df!r}")
    tail = 0.5 * _regularized_beta(df / 2, 0.5, df / (df + t * t))
    return 1 - tail if t > 0 else tail


def _regularized_beta(a: float, b: float, x: float) -> float:
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    front = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1 - x))
    if x < (a + 1) / (a + b + 2):
        return front * _continued_fraction(a, b, x) / a
    return 1 - front * _continued_fraction(b, a, 1 - x) / b


def _continued_fraction(a: float, b: float, x: float) -> float:
    c, d = 1.0, _nonzero(1 - (a + b) * x / (a + 1))
    d = 1 / d
    result = d
    for m in range(1, MAX_TERMS + 1):
        for numerator in (m * (b - m) * x / ((a + 2 * m - 1) * (a + 2 * m)),
                          -(a + m) * (a + b + m) * x / ((a + 2 * m) * (a + 2 * m + 1))):  # fmt: skip
            d = 1 / _nonzero(1 + numerator * d)
            c = _nonzero(1 + numerator / c)
            result *= d * c
        if abs(d * c - 1) < TOLERANCE:
            break
    return result


def _nonzero(value: float) -> float:
    return TINY if abs(value) < TINY else value
