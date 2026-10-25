"""The forward of an expiry from put-call parity (G13 section 1). `parity_forward` is one strike's value, kept a
standalone pure function so story G7b part d can import it for protocol v4's 1.4 forward (its builder's request)."""

from __future__ import annotations

import math
from collections.abc import Sequence

from .constants import DAYS_PER_YEAR, FORWARD_STRIKES


def parity_forward(strike: float, call_mid: float, put_mid: float, rate: float, days: int) -> float:
    """`F = K + e^{r days/365} (C - P)` for European options on a future."""
    return strike + math.exp(rate * days / DAYS_PER_YEAR) * (call_mid - put_mid)


def averaged_forward(pairs: Sequence[tuple[float, float, float]], rate: float, days: int) -> float | None:
    """The mean parity forward of the `FORWARD_STRIKES` strikes whose call and put mids are closest; `pairs` are
    `(strike, call_mid, put_mid)`. None without any pair."""
    if not pairs:
        return None
    nearest = sorted(pairs, key=lambda p: (abs(p[1] - p[2]), p[0]))[:FORWARD_STRIKES]
    return sum(parity_forward(k, c, p, rate, days) for k, c, p in nearest) / len(nearest)
