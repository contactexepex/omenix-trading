"""Student t with 4 degrees of freedom: its quantile in closed form (no scipy), as G7's `v6_ewma_t4` uses the law."""

from __future__ import annotations

import math


def t4_quantile(p: float) -> float:
    """`t = sign(p - 1/2) x 2 sqrt(q - 1)`, `q = cos(arccos(sqrt(a)) / 3) / sqrt(a)`, `a = 4 p (1 - p)`."""
    if not 0 < p < 1:
        raise ValueError(f"a quantile level must be inside (0, 1): {p}")
    if p == 0.5:
        return 0.0
    a = 4 * p * (1 - p)
    q = math.cos(math.acos(math.sqrt(a)) / 3) / math.sqrt(a)
    return math.copysign(2 * math.sqrt(q - 1), p - 0.5)
