"""Bootstrap and percentile conventions of experiment 1's protocol (section 7; story B3).

- Opportunity bootstrap: numpy `default_rng(seed)`; one draw `rng.integers(0, n, size=(resamples, n))` (resample r
  takes opportunities idx[r]); statistic = mean net per opportunity; means sorted ascending; the lower bound is the
  value at `lower_bound_index` (0-based), no interpolation.
- Year-block bootstrap (sensitivity): whole calendar years drawn the same way, `rng.integers(0, years, size=(resamples,
  years))`; statistic = total net of the drawn years divided by their opportunity count.
- Monte Carlo error of the lower bound (reported only): sample standard deviation (ddof 1) of the lower bounds with
  seeds seed + 1 ... seed + repeats.
- Percentile p of n values (C1 threshold): nearest rank, the ascending value at index ceil(p x n) - 1.
Numbers are never rounded here. numpy's generator streams are stable within a numpy version; the results record it.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np

from .experiments import StatisticsTerms


def resampled_means(values: Sequence[float], resamples: int, seed: int) -> np.ndarray:
    data = np.asarray(values, dtype=float)
    draws = np.random.default_rng(seed).integers(0, len(data), size=(resamples, len(data)))
    return np.sort(data[draws].mean(axis=1))


def lower_bound(values: Sequence[float], terms: StatisticsTerms, seed: int | None = None) -> float:
    means = resampled_means(values, terms.resamples, terms.seed if seed is None else seed)
    return float(means[terms.lower_bound_index])


def year_block_lower_bound(values_by_year: Sequence[Sequence[float]], terms: StatisticsTerms) -> float:
    sums = np.array([sum(year) for year in values_by_year], dtype=float)
    counts = np.array([len(year) for year in values_by_year], dtype=float)
    draws = np.random.default_rng(terms.seed).integers(0, len(sums), size=(terms.resamples, len(sums)))
    means = np.sort(sums[draws].sum(axis=1) / counts[draws].sum(axis=1))
    return float(means[terms.lower_bound_index])


def monte_carlo_error(values: Sequence[float], terms: StatisticsTerms) -> float:
    bounds = [lower_bound(values, terms, terms.seed + k) for k in range(1, terms.mc_repeats + 1)]
    return float(np.std(bounds, ddof=1))


def nearest_rank(values: Sequence[float], p: float) -> float:
    ordered = sorted(values)
    return float(ordered[math.ceil(p * len(ordered)) - 1])
