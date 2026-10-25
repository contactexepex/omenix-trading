"""One unit's score over a period (story F9a; S1 `role_value_minimum_sample`). Applicable opportunities are the scored
pairs on days the unit was ablated and its card consulted; the paired difference is with the unit minus without it (0
when the two decisions agree). Each opportunity's net value is its difference minus its own day's cost (review 124:
the cost covers the same dates as the tested net). The bootstrap is S3's moving-block resampler
(`fno/scoreboard/uncertainty.py`, imported) on the net values in date order with a risk of 1 each, so its ratio is the
mean: blocks of 20 observations (not 20 sessions), 10,000 resamples, seed 20261014. Each block's calendar span and the
sample's months are printed beside the p-values, because the resampler's coverage on sparse ablations is unvalidated.
Its 5th and 95th nearest-rank percentiles are printed only; the verdict comes from Holm. The risk effects (worst month,
maximum loss) are printed beside the verdict and never decide it (owner, 15 Oct 2026: "money only, risk shown")."""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from ..scoreboard.series import DailySeries
from ..scoreboard.uncertainty import BLOCK_DAYS, p_value, resampled_ratios
from .cost import mean_cost

LOWER_PERCENTILE, UPPER_PERCENTILE = 5, 95  # provisional, to confirm at the S1 freeze (response 166, question 1)


@dataclass(frozen=True)
class Opportunity:
    day: date
    difference: float
    changed: bool
    max_loss_difference: float
    cost: float | None  # the unit's part of the book's cost that day, rupees; None: unknown


@dataclass(frozen=True)
class UnitScore:
    unit: str
    applicable: int
    changed: int
    mean_difference: float | None
    cost: float | None  # mean cost on the scored dates, rupees; None: unknown
    mean_net_value: float | None
    interval: tuple[float, float] | None  # printed only
    p_earns: float | None  # one-sided: "net value above zero"
    p_drop: float | None  # one-sided: "net value below zero"
    worst_month: tuple[str, float] | None
    mean_max_loss_difference: float | None  # over changed opportunities
    operating_cost: float | None = None  # mean over every consulted day of the period, shown apart
    block_spans: tuple[tuple[date, date], ...] = ()  # each block of 20 observations, first and last date
    months: tuple[tuple[str, int], ...] = ()  # observations per month


def _series(days: Sequence[date], values: Sequence[float]) -> DailySeries:
    return DailySeries(tuple(days), tuple(values), tuple(1.0 for _ in values))


def percentile(sorted_values: Sequence[float], p: int) -> float:
    return sorted_values[max(math.ceil(p / 100 * len(sorted_values)) - 1, 0)]


def worst_month(opportunities: Sequence[Opportunity]) -> tuple[str, float] | None:
    months: dict[str, float] = {}
    for o in opportunities:
        months[o.day.strftime("%Y-%m")] = months.get(o.day.strftime("%Y-%m"), 0.0) + o.difference
    return min(((m, round(v, 2)) for m, v in months.items()), key=lambda mv: (mv[1], mv[0])) if months else None


def spread(days: Sequence[date]) -> tuple[tuple[tuple[date, date], ...], tuple[tuple[str, int], ...]]:
    """The calendar span of each consecutive block of 20 observations, and the observations per month."""
    blocks = tuple((days[i], days[min(i + BLOCK_DAYS, len(days)) - 1]) for i in range(0, len(days), BLOCK_DAYS))
    return blocks, tuple(sorted(Counter(d.strftime("%Y-%m") for d in days).items()))


def score_unit(unit: str, opportunities: Sequence[Opportunity], operating_cost: float | None = None) -> UnitScore:
    found = sorted(opportunities, key=lambda o: o.day)
    n, changed, days = len(found), [o for o in found if o.changed], [o.day for o in found]
    mean = round(sum(o.difference for o in found) / n, 2) if n else None
    risk = round(sum(o.max_loss_difference for o in changed) / len(changed), 2) if changed else None
    cost, (blocks, months) = mean_cost(o.cost for o in found), spread(days)
    shown = {"operating_cost": operating_cost, "block_spans": blocks, "months": months}
    if cost is None:
        return UnitScore(unit, n, len(changed), mean, None, None, None, None, None, worst_month(found), risk, **shown)
    values = [o.difference - o.cost for o in found]
    ratios = resampled_ratios(_series(days, values))
    interval = None if ratios is None else (percentile(ratios, LOWER_PERCENTILE), percentile(ratios, UPPER_PERCENTILE))
    return UnitScore(
        unit, n, len(changed), mean, cost, round(sum(values) / n, 2),
        None if interval is None else (round(interval[0], 2), round(interval[1], 2)),
        p_value(_series(days, values)), p_value(_series(days, [-v for v in values])), worst_month(found), risk,
        **shown,
    )  # fmt: skip
