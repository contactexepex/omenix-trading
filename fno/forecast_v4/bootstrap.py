"""The v4 comparison statistics (PROTOCOL_v4.md section 5): the moving-block resampling, the minimum-effect gate, the
futility bound, and two sensitivities that are reported, never confirmatory: the centred bootstrap of revision 0 (it
over-rejects, `research/forecasts/v4_null_calibration.md`) and HAC. The confirmatory test is `confirmatory.py`.

Resampling, for n paired values in date order and block length L: each of B resamples draws ceil(n / L) block starts
uniformly from 0 .. n - L with replacement (numpy `default_rng(SeedSequence(words)).integers`, all starts in one draw of
shape (B, ceil(n / L)), row r being resample r), joins the blocks in draw order and cuts to n. The significance test
seeds with words [BOOTSTRAP_SEED, k], the futility bound with [BOOTSTRAP_SEED, k, 1, look number].
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from statistics import NormalDist

import numpy as np

from .pairs import PairedSet
from .terms import BOOTSTRAP_SEED, FUTILITY_CONFIDENCE, LOOK_NUMBER, RESAMPLES

FUTILITY_SEED_WORD = 1


@dataclass(frozen=True)
class OneSidedTest:
    n: int
    mean_difference: float | None  # D; negative favours the forecaster
    p_value: float  # 1.0 when not tested
    tested: bool  # False with fewer than 2L pairs


@dataclass(frozen=True)
class EffectCheck:
    n: int
    relative_improvement: float | None  # -mean(d) / mean(baseline loss) on the gate set
    meets_minimum_effect: bool
    upper_bound: float | None  # one-sided 97.5% upper bound of the relative improvement at this look
    futile: bool  # upper bound below the minimum effect; never True when not assessable


def block_indices(n: int, block: int, words: Sequence[int], resamples: int = RESAMPLES) -> np.ndarray:
    blocks = math.ceil(n / block)
    rng = np.random.default_rng(np.random.SeedSequence(list(words)))
    starts = rng.integers(0, n - block + 1, size=(resamples, blocks))
    return (starts[:, :, None] + np.arange(block)).reshape(resamples, blocks * block)[:, :n]


def one_sided_test(differences: Sequence[float], block: int, k: int, resamples: int = RESAMPLES) -> OneSidedTest:
    """Reported only. p = (1 + #{b : D*_b - D <= D}) / (B + 1), the resampled means centred on the observed mean."""
    n = len(differences)
    if n < 2 * block:
        return OneSidedTest(n, float(np.mean(differences)) if n else None, 1.0, False)
    values = np.asarray(differences, dtype=float)
    observed = float(values.mean())
    means = values[block_indices(n, block, [BOOTSTRAP_SEED, k], resamples)].mean(axis=1)
    hits = int(np.count_nonzero(means - observed <= observed))
    return OneSidedTest(n, observed, (1 + hits) / (resamples + 1), True)


def relative_improvement(gate: PairedSet) -> float:
    """-mean(d) / mean(baseline loss): 0.03 is "3% lower mean textbook QLIKE", 0.02 is a Brier skill score of 0.02."""
    base = math.fsum(gate.baseline_losses)
    if base <= 0:
        raise ValueError("the baseline's mean loss on the gate set must be > 0 to size an effect")
    return -math.fsum(gate.differences) / base


def effect_check(
    gate: PairedSet, margin: float, block: int, k: int, look: str, resamples: int = RESAMPLES
) -> EffectCheck:
    """The minimum-effect gate and futility on the gate set at a look. The bound recomputes the ratio of means on each
    resample (pairs kept together) and takes the nearest-rank 97.5th percentile (the 9,750th of 10,000)."""
    n = len(gate.differences)
    if n == 0:
        return EffectCheck(0, None, False, None, False)
    observed = relative_improvement(gate)
    if n < 2 * block:
        return EffectCheck(n, observed, observed >= margin, None, False)
    index = block_indices(n, block, [BOOTSTRAP_SEED, k, FUTILITY_SEED_WORD, LOOK_NUMBER[look]], resamples)
    d, base = np.asarray(gate.differences)[index], np.asarray(gate.baseline_losses)[index]
    ratios = np.sort(-d.sum(axis=1) / base.sum(axis=1))
    upper = float(ratios[math.ceil(FUTILITY_CONFIDENCE * resamples) - 1])
    return EffectCheck(n, observed, observed >= margin, upper, upper < margin)


def hac_one_sided_p(differences: Sequence[float], block: int) -> float | None:
    """Sensitivity only: Newey-West (Bartlett, lag L - 1) t of the mean, one-sided normal p = Phi(t). None when it
    cannot be computed (fewer than 2L pairs, or a zero long-run variance)."""
    n = len(differences)
    if n < 2 * block:
        return None
    x = np.asarray(differences, dtype=float)
    e = x - x.mean()
    lag = block - 1
    variance = float(e @ e) / n
    for j in range(1, lag + 1):
        variance += 2 * (1 - j / (lag + 1)) * float(e[j:] @ e[:-j]) / n
    if variance <= 0:
        return None
    return NormalDist().cdf(float(x.mean()) / math.sqrt(variance / n))
