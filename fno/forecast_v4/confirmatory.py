"""The confirmatory test of protocol v4 (PROTOCOL_v4.md section 5, revision 1 after ChatGPT review 99).

The centred moving-block bootstrap of revision 0 over-rejected true nulls in a seeded simulation (about 25% at a
nominal 5% with n = 2L, 6-13% at n = 125; `research/forecasts/v4_null_calibration.md`), so it is no longer
confirmatory. The confirmatory p is the larger of two studentized tests, so both must pass:

1. **Batch means t:** the most recent k x L pairs (k = floor(n / L), the earliest n - kL dropped) cut into k
   consecutive batches of L; t = mean / (SD of batch means / sqrt k); one-sided p = P(T_(k-1) <= t).
2. **Studentized moving-block bootstrap:** resamples as `bootstrap.block_indices` with seed words [BOOTSTRAP_SEED, k,
   2]; each resample's t* = (D*_b - D) / se*_b with se* from the same batch layout; p = (1 + #{t*_b <= t}) / (B + 1).
   A resample whose se* is 0 counts as no hit.

Fewer than 2L pairs, or a zero observed SE: not tested, p = 1.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np

from .bootstrap import OneSidedTest, block_indices
from .student_t import t_cdf
from .terms import BOOTSTRAP_SEED, RESAMPLES

STUDENTIZED_SEED_WORD = 2
MIN_CLAIM_BATCHES = 12  # rules E+D and F+D: fewer batches give neither a claim nor a futility "no"
FUTILITY_LEVEL = 0.025  # per member and look (Bonferroni 2 x 2.5% over the two looks)
MIN_EVENT_DAYS = 5  # every member (revision 8): fewer 2% days in the scored window give no claim and no "no"
EVENT_BANDS = ((5, 7), (8, 12), (13, None))  # revision 5: each band has its own Brier thresholds
CRASH_SHARE = 0.10  # owner, item E option 2 (15 Oct 2026): a window with more 2% days than this share is cut


def batch_layout(n: int, block: int) -> tuple[int, int]:
    """(first index used, number of batches)."""
    batches = n // block
    return n - batches * block, batches


def batch_standard_error(values: np.ndarray, block: int) -> np.ndarray:
    """SE of the mean from consecutive batch means along the last axis (works on one series or a resample matrix)."""
    first, batches = batch_layout(values.shape[-1], block)
    means = values[..., first:].reshape(*values.shape[:-1], batches, block).mean(axis=-1)
    return means.std(axis=-1, ddof=1) / math.sqrt(batches)


def batch_means_p(differences: Sequence[float], block: int) -> float:
    x = np.asarray(differences, dtype=float)
    if len(x) < 2 * block:
        return 1.0
    first, batches = batch_layout(len(x), block)
    se = float(batch_standard_error(x, block))
    if se == 0:
        return 1.0
    return t_cdf(float(x[first:].mean()) / se, batches - 1)


def studentized_bootstrap_p(differences: Sequence[float], block: int, k: int, resamples: int = RESAMPLES) -> float:
    x = np.asarray(differences, dtype=float)
    n = len(x)
    if n < 2 * block:
        return 1.0
    se = float(batch_standard_error(x, block))
    if se == 0:
        return 1.0
    observed = float(x.mean())
    sample = x[block_indices(n, block, [BOOTSTRAP_SEED, k, STUDENTIZED_SEED_WORD], resamples)]
    se_star = batch_standard_error(sample, block)
    valid = se_star > 0
    t_star = (sample.mean(axis=1)[valid] - observed) / se_star[valid]
    return (1 + int(np.count_nonzero(t_star <= observed / se))) / (resamples + 1)


def confirmatory_test(differences: Sequence[float], block: int, k: int, resamples: int = RESAMPLES) -> OneSidedTest:
    """p = max(batch means t, studentized block bootstrap): the member's p for Holm."""
    n = len(differences)
    mean = float(np.mean(differences)) if n else None
    if n < 2 * block:
        return OneSidedTest(n, mean, 1.0, False)
    p = max(batch_means_p(differences, block), studentized_bootstrap_p(differences, block, k, resamples))
    return OneSidedTest(n, mean, p, True)


def hall_t(t: float, skew: float, batches: int) -> float:
    """Hall's (1992) monotone skewness correction of a t statistic computed from `batches` values whose sample
    skewness is `skew`: t + skew (1 + 2 t^2) / (6 sqrt k) + skew^2 t^3 / (27 k)."""
    root = math.sqrt(batches)
    return t + skew * (1 + 2 * t * t) / (6 * root) + skew * skew * t**3 / (27 * batches)


def calibrated_p(differences: Sequence[float], block: int, threshold: float, step: float) -> float:
    """Rule E+D (revision 2, the operative claim rule): the member's p for the family, `step x p_t / threshold`
    capped at 1, so it is at or below the family's first step (rate / 15) exactly when the batch-means t p-value p_t
    is at or below the member's worst-case calibrated threshold (`tools/v4_claim_thresholds.py`, at the look's n).
    Fewer than 12 whole batches, or no threshold: 1."""
    if len(differences) // block < MIN_CLAIM_BATCHES or threshold <= 0:
        return 1.0
    return min(1.0, step * batch_means_p(differences, block) / threshold)


def futility_p(
    differences: Sequence[float], baseline_losses: Sequence[float], block: int, margin: float, threshold: float
) -> float:
    """Rule F+D (revision 3, the operative futility rule): the member's futility p on the gate set, for "the true
    relative improvement is below the minimum effect". With e_t = d_t + margin x b_t, that is mean(e) > 0; its
    batch-means t p-value p_e is mapped to `0.025 x p_e / threshold` (capped at 1), so a member is futile at a look when
    this is at most 0.025, i.e. p_e at or below its worst-case calibrated threshold (`tools/v4_futility_study.py`, at
    the look's n). Fewer than 12 whole batches, or no threshold: 1 (no "no")."""
    if len(differences) // block < MIN_CLAIM_BATCHES or threshold <= 0:
        return 1.0
    excess = -(np.asarray(differences, dtype=float) + margin * np.asarray(baseline_losses, dtype=float))
    return min(1.0, FUTILITY_LEVEL * batch_means_p(excess, block) / threshold)


def judgeable(event_days: int) -> bool:
    """Revision 4 (judge 98 addendum 3) for the Brier members, revision 8 (judge 98 addendum 7) for every member: a
    member is judged at a look only when its scored window holds at least 5 sessions with an absolute NIFTY move of 2%
    or more; otherwise it is not judgeable at that look (p = 1 for claims and futility: undecided, never "no"). Calm
    windows otherwise gave V1 false claims and a false "no" well above nominal (`tools/v4_regime_stress.py`)."""
    return event_days >= MIN_EVENT_DAYS


def crash_dominated(event_days: int, n: int) -> bool:
    """Owner's item E, option 2 (15 Oct 2026; orchestrator decision 69): a scored window of n outcomes whose share of
    2% days is above 10% (strict) is not judgeable at that look, for every member, like a window below the 5-day gate
    (p = 1 for claims and futility: undecided, never "no"). Measured in `tools/v4_crash_cut.py`. At n = 125 a
    judgeable window holds at most 12 2% days, so the 13+ band is reachable only from n = 130."""
    return event_days > CRASH_SHARE * n


def event_band(event_days: int) -> tuple[int, int | None] | None:
    """Revision 5 (judge 98 addendum 4): the band of a Brier member's 2%-day count, which selects its claim and
    futility thresholds (`tools/v4_brier_bands.py`); None below the gate (not judgeable)."""
    for band in EVENT_BANDS:
        low, high = band
        if event_days >= low and (high is None or event_days <= high):
            return band
    return None
