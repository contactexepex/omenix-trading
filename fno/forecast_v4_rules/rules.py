"""Protocol v4's close-based rule forecasters (stories G7 and G7b), with zero fitted parameters (design 5.7 rule 5).

- `v6_ewma_t4` (V6a, V6b; reported only, decision 70): `p1 = P(abs(X) >= 2%)`, `X = s T / sqrt(2)`, `T` Student's t
  with 4 degrees of freedom (variance 2, so `X` has variance `s^2`), `s^2` the EWMA close-proxy session variance;
  V6b = `1 - (1 - p1)^5` (independent sessions, reasoning only).
- `close_blend`: the mean of the HAR daily and EWMA variance forecasts at the question's horizon, used as
  `v1_close_blend` (V1's `rules` slot), `v2_close_blend` (V2's `rules` slot) and `v3_close_blend` (V3, reported).
"""

from __future__ import annotations

import math

from ..forecast_v4.student_t import t_cdf
from ..forecast_v4.terms import BIG_MOVE
from .baselines import MISSING, OK, Value

T_DEGREES = 4  # fat tails of daily index returns (reasoning only; fixed, not fitted)
V6B_SESSIONS = 5


def big_move_probability(session_variance: float) -> float:
    """P(abs(X) >= 2%) for X = s T / sqrt(2), T ~ t(4)."""
    scaled = BIG_MOVE * math.sqrt(T_DEGREES / (T_DEGREES - 2)) / math.sqrt(session_variance)
    return 2 * (1 - t_cdf(scaled, T_DEGREES))


def v6_ewma_t4(session_variance: Value) -> tuple[Value, Value]:
    """(V6a, V6b) from the EWMA variance at the last session before the cutoff."""
    if session_variance.status != OK:
        return session_variance, session_variance
    p1 = big_move_probability(session_variance.value)
    return Value.of(p1, positive=False), Value.of(1 - (1 - p1) ** V6B_SESSIONS, positive=False)


def close_blend(har_daily: Value, ewma: Value) -> Value:
    """Missing when either input is not a value."""
    if har_daily.status != OK or ewma.status != OK:
        return Value(MISSING)
    return Value.of((har_daily.value + ewma.value) / 2)
