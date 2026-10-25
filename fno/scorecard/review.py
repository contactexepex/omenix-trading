"""A strategy version's statistical review (story E6, criteria 2 and 4; design 6 and 12.8): only on a review date of
its evaluation plan, and only once the paper gate is met (enough completed positions and months since the first entry:
a minimum, not proof). Open positions are never counted.

The rule is **provisional until S1** (the evaluation protocol): its statistics live in one place, config.yaml
`scorecard_review`, which S1 replaces without a code change (orchestrator, 14 Oct 2026; reasoning only); the gate is
design 6's, the same constant D2's allocation uses (`UNPROVEN_BELOW_COMPLETED_TRADES`, `PAPER_GATE_MONTHS`):
- sample: the C1 net of each completed position; its mean with a two-sided interval from experiment 1's seeded
  bootstrap of the mean (`resampled_means`, nearest-rank tails);
- **retire** when the interval's upper end is below the plan's expected low (worse than planned, beyond doubt);
- **pause** when the mean is below the expected low but the interval still reaches it;
- **keep** otherwise;
- **net profit shown** only when the interval's lower end and the version's whole net (legging costs included) are
  above zero; anything else is inconclusive. Even then nothing is promoted: real money is always the owner's decision.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date

from ..constants import (
    PAPER_GATE_MONTHS,
    REVIEW_KEEP,
    REVIEW_PAUSE,
    REVIEW_RETIRE,
    UNPROVEN_BELOW_COMPLETED_TRADES,
)
from ..research_engine.statistics import resampled_means

OWNER_DECIDES = "the owner may discuss real money (never automatic)"


@dataclass(frozen=True)
class ReviewTerms:
    status: str  # "provisional until S1" until the evaluation protocol freezes the real statistics
    min_positions: int
    min_months: int
    confidence: float
    resamples: int
    seed: int


def review_terms(cfg: Mapping) -> ReviewTerms:
    block = cfg["scorecard_review"]
    return ReviewTerms(
        str(block["status"]), UNPROVEN_BELOW_COMPLETED_TRADES, PAPER_GATE_MONTHS, float(block["confidence"]),
        int(block["bootstrap_resamples"]), int(block["bootstrap_seed"]),
    )  # fmt: skip


@dataclass(frozen=True)
class Review:
    on: date
    review_date: bool
    positions: int
    months: int
    gate_met: bool
    mean_rs: float | None
    interval_rs: tuple[float, float] | None
    decision: str | None  # keep, pause or retire; None when nothing is decided today
    profit_shown: bool  # the bar for the owner's real-money discussion; never a promotion by itself
    reason: str
    terms_status: str


def full_months(start: date, end: date) -> int:
    months = (end.year - start.year) * 12 + end.month - start.month
    return months - (end.day < start.day)


def interval(values: Sequence[float], terms: ReviewTerms) -> tuple[float, float]:
    means = resampled_means(values, terms.resamples, terms.seed)
    tail = (1 - terms.confidence) / 2
    return tuple(float(means[math.ceil(p * terms.resamples) - 1]) for p in (tail, 1 - tail))


def decide(mean: float, low_high: tuple[float, float], expected_low: float) -> tuple[str, str]:
    low, high = low_high
    if high < expected_low:
        return REVIEW_RETIRE, f"the interval's upper end Rs {high:,.2f} is below the expected low"
    if mean < expected_low:
        return REVIEW_PAUSE, f"mean Rs {mean:,.2f} is below the expected low; the interval still reaches it"
    return REVIEW_KEEP, f"mean Rs {mean:,.2f} is at or above the expected low Rs {expected_low:,.2f}"


def review(nets: Sequence[float], total_net: float, first_entry: date | None, plan: dict, on: date,
           terms: ReviewTerms) -> Review:  # fmt: skip
    """`nets`: each completed position's C1 net; `total_net`: the version's whole net (legging costs included)."""
    review_date = on in plan["review_dates"]
    months = full_months(first_entry, on) if first_entry else 0
    gate = len(nets) >= terms.min_positions and months >= terms.min_months
    mean = sum(nets) / len(nets) if nets else None
    bounds = interval(nets, terms) if len(nets) >= 2 else None
    shape = (on, review_date, len(nets), months, gate, mean, bounds)
    if not review_date:
        return Review(*shape, None, False, "not a review date of the plan: no statistical decision", terms.status)
    if not gate:
        need = f"{len(nets)} of {terms.min_positions} positions, {months} of {terms.min_months} months"
        return Review(*shape, REVIEW_KEEP, False, f"keep: the gate is not met ({need}); not judged", terms.status)
    decision, why = decide(mean, bounds, plan["expected_range"][0])
    shown = bounds[0] > 0 and total_net > 0
    proof = f"net profit shown: {OWNER_DECIDES}" if shown else "inconclusive: no net profit shown"
    return Review(*shape, decision, shown, f"{decision}: {why}; {proof}", terms.status)
