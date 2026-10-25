"""The comparison statistics of protocol section 8 (story G4): the moving-block bootstrap of a mean Brier difference,
its two-sided p-value, its unadjusted 95% interval and Holm's step-down over the primary family.

For `n` paired dates (date order): each of B = 10,000 resamples draws `ceil(n / L)` block starts uniformly from
`0 .. n - L` with replacement (L = 20), joins the blocks in draw order, cuts to `n` values and takes the mean. Random
numbers: `numpy.random.default_rng(SeedSequence([20261013, k]))` for comparison `k`, all starts in one draw of shape
(B, ceil(n / L)), row r being resample r. p = (1 + #{b : |D*_b - D| >= |D|}) / (B + 1). Interval: the 2.5% and 97.5%
percentiles of the D*_b with numpy's default (linear) percentile, labelled "unadjusted 95%". Fewer than 40 paired dates
(2L): not tested, p = 1. Constants come from the frozen `comparisons.py`.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from ..forecast.comparisons import BLOCK_LENGTH, BOOTSTRAP_SEED, FAMILY_ERROR_RATE, MIN_PAIRED_DATES, RESAMPLES

INTERVAL_PERCENTILES = (2.5, 97.5)


@dataclass(frozen=True)
class BootstrapResult:
    n: int
    mean_difference: float | None  # D: mean Brier(first) - Brier(second); negative favours `first`
    p_value: float  # two-sided; 1.0 when not tested
    interval: tuple[float, float] | None  # unadjusted 95%
    tested: bool  # False: fewer than 40 paired dates


def resampled_means(differences: Sequence[float], k: int, resamples: int = RESAMPLES,
                    block: int = BLOCK_LENGTH) -> np.ndarray:  # fmt: skip
    """`block`: the block length; G4's 20 sessions by default (EDGE1 passes 2 trades, its protocol section 11)."""
    values = np.asarray(differences, dtype=float)
    n = len(values)
    blocks = math.ceil(n / block)
    rng = np.random.default_rng(np.random.SeedSequence([BOOTSTRAP_SEED, k]))
    starts = rng.integers(0, n - block + 1, size=(resamples, blocks))
    index = (starts[:, :, None] + np.arange(block)).reshape(resamples, blocks * block)[:, :n]
    return values[index].mean(axis=1)


def compare(differences: Sequence[float], k: int) -> BootstrapResult:
    """The bootstrap of comparison `k` on its paired differences, in date order."""
    n = len(differences)
    if n < MIN_PAIRED_DATES:
        return BootstrapResult(n, sum(differences) / n if n else None, 1.0, None, False)
    observed = float(np.mean(differences))
    means = resampled_means(differences, k)
    extreme = int(np.count_nonzero(np.abs(means - observed) >= abs(observed)))
    low, high = np.percentile(means, INTERVAL_PERCENTILES)
    return BootstrapResult(n, observed, (1 + extreme) / (len(means) + 1), (float(low), float(high)), True)


def holm_significant(p_values: Sequence[float], rate: float = FAMILY_ERROR_RATE) -> list[bool]:
    """Holm's step-down: sorted ascending, the i-th (1-based) is significant while p <= rate / (m - i + 1); the first
    failure stops it. Returned in the input order."""
    m = len(p_values)
    significant = [False] * m
    for rank, i in enumerate(sorted(range(m), key=lambda j: p_values[j]), start=1):
        if p_values[i] > rate / (m - rank + 1):
            break
        significant[i] = True
    return significant
