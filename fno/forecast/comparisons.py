"""The forecast comparisons (story G1; PROTOCOL.md section 8, as changed by ChatGPT review 28 and response 60).

**Primary (confirmatory) family: 10 tests.** For each question, Book 2 against Book 1 and Book 3 against Book 1
(does AI judgement, then the full AI system, read the market better than the rules?). Each is a mean Brier
difference with a moving-block bootstrap, adjusted together by Holm's step-down at a family-wise error rate of 5%.
Comparison k (1-based, in this order) seeds its bootstrap with `SeedSequence([BOOTSTRAP_SEED, k])`.

**Secondary (descriptive only):** Book 2 against Book 3 and every book against each of the question's baselines,
plus log scores and calibration. Effect sizes and unadjusted intervals only; never tested, never called confirmatory.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..constants import (
    BASELINE_BASE_RATE,
    BASELINE_MODEL,
    BASELINE_RISK_NEUTRAL,
    BOOK1_RULES,
    BOOK2_HYBRID,
    BOOK3_AI,
    BOOKS,
    FORECAST_Q1_UP_20D,
    FORECAST_Q2_MOVE_3PCT_20D,
    FORECAST_QUESTIONS,
)

BLOCK_LENGTH = 20  # trading days, moving-block bootstrap
RESAMPLES = 10_000
BOOTSTRAP_SEED = 20261013
FAMILY_ERROR_RATE = 0.05  # Holm's step-down over the primary family only
MIN_PAIRED_DATES = 2 * BLOCK_LENGTH  # fewer: not tested, p = 1
PRIMARY_PAIRS = ((BOOK2_HYBRID, BOOK1_RULES), (BOOK3_AI, BOOK1_RULES))


@dataclass(frozen=True)
class Comparison:
    k: int  # 1-based position (the primary family's bootstrap seed word; secondary ones are numbered after it)
    question: str
    first: str  # D = Brier(first) - Brier(second); negative favours `first`
    second: str
    primary: bool


def baselines_for(question: str) -> tuple[str, str]:
    """Questions 1-2: risk-neutral and base rate; questions 3-5: base rate and the statistical model."""
    if question in (FORECAST_Q1_UP_20D, FORECAST_Q2_MOVE_3PCT_20D):
        return BASELINE_RISK_NEUTRAL, BASELINE_BASE_RATE
    return BASELINE_BASE_RATE, BASELINE_MODEL


def _secondary_pairs(question: str) -> list[tuple[str, str]]:
    return [(BOOK2_HYBRID, BOOK3_AI)] + [(book, base) for base in baselines_for(question) for book in BOOKS]


def primary_family() -> tuple[Comparison, ...]:
    """The 10 confirmatory tests, in their numbered order: questions 1 to 5, each Book 2 then Book 3 against Book 1."""
    pairs = [(q, a, b) for q in FORECAST_QUESTIONS for a, b in PRIMARY_PAIRS]
    return tuple(Comparison(k, q, a, b, True) for k, (q, a, b) in enumerate(pairs, start=1))


def secondary_comparisons() -> tuple[Comparison, ...]:
    """Descriptive comparisons (effect sizes and intervals only), numbered after the primary family."""
    pairs = [(q, a, b) for q in FORECAST_QUESTIONS for a, b in _secondary_pairs(q)]
    first = len(primary_family()) + 1
    return tuple(Comparison(k, q, a, b, False) for k, (q, a, b) in enumerate(pairs, start=first))
