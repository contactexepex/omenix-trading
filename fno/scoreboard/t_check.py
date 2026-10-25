"""S1's t-based check beside the bootstrap (story S6 section 3; owner, 15 Oct 2026, "S1's t-based check is a printed
warning, not a pass condition"): a one-sided 95% t bound of net per unit of risk on k whole blocks of 20 sessions
counted back from the last, with the ratio estimator's linearisation z_b = (net_b - R x risk_b) / mean(risk_b). It
never changes `claim_allowed`; it only flags a disagreement with the bootstrap."""

from __future__ import annotations

import math
import statistics

from .series import DailySeries
from .uncertainty import BLOCK_DAYS

# One-sided 95% Student t quantiles, 1 to 30 degrees of freedom (scipy is not installed); above 30 the 30 value, which
# is slightly wider, so cautious.
T95 = (6.314, 2.920, 2.353, 2.132, 2.015, 1.943, 1.895, 1.860, 1.833, 1.812, 1.796, 1.782, 1.771, 1.761, 1.753, 1.746,
       1.740, 1.734, 1.729, 1.725, 1.721, 1.717, 1.714, 1.711, 1.708, 1.706, 1.703, 1.701, 1.699, 1.697)  # fmt: skip
DISAGREES = "t-check disagrees: warning"


def t_quantile(df: int) -> float:
    return T95[min(df, len(T95)) - 1]


def t_bound(series: DailySeries) -> tuple[float | None, int, int]:
    """(bound, whole blocks k, sessions left out); the bound is None below two blocks or with no risk in them."""
    n = len(series.days)
    k, left_out = n // BLOCK_DAYS, n % BLOCK_DAYS
    blocks = [(sum(series.net[s : s + BLOCK_DAYS]), sum(series.risk[s : s + BLOCK_DAYS]))
              for s in range(left_out, n, BLOCK_DAYS)]  # fmt: skip
    risk = sum(r for _, r in blocks)
    if k < 2 or risk <= 0:
        return None, k, left_out
    ratio, mean_risk = sum(net for net, _ in blocks) / risk, risk / k
    z = [(net - ratio * r) / mean_risk for net, r in blocks]
    return ratio - t_quantile(k - 1) * statistics.stdev(z) / math.sqrt(k), k, left_out


def t_check(series: DailySeries, bootstrap_bound: float | None) -> dict:
    bound, k, left_out = t_bound(series)
    agrees = None if bound is None or bootstrap_bound is None else (bound > 0) == (bootstrap_bound > 0)
    return {"lower_bound": None if bound is None else round(bound, 6), "blocks": k, "left_out_sessions": left_out,
            "agrees_with_bootstrap": agrees}  # fmt: skip
