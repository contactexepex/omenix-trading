"""Experiment 1's controls (story B3, protocol section 6).

C1 random timing, for one conditional policy: its count of each action (P5: k SC and m BF) is given to that many
randomly chosen opportunities of the same period, without replacement, no trade elsewhere; every opportunity scores
exactly as for the policy (a chosen opportunity that did not trade scores 0). Convention: numpy `default_rng(seed)`; per
sequence `order = rng.permutation(n)`; actions in sorted code order take consecutive slices of `order` (the first k
positions to the first code, and so on); a sequence's total is the sum of its chosen P&L in that order.
C2 opposite condition is an ordinary rule policy (experiment_1.py), scored like any policy.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence

import numpy as np

from .opportunities import Action


def random_timing_totals(
    chosen: Sequence[Action], pnl_by_action: Mapping[str, Sequence[float]], runs: int, seed: int
) -> list[float]:
    """Total net of each of `runs` random sequences with the same action counts as `chosen`."""
    counts = sorted(Counter(a for a in chosen if a is not None).items())
    rng = np.random.default_rng(seed)
    totals = []
    for _ in range(runs):
        order, start, total = rng.permutation(len(chosen)), 0, 0.0
        for action, count in counts:
            for index in order[start : start + count]:
                total += pnl_by_action[action][index]
            start += count
        totals.append(total)
    return totals
