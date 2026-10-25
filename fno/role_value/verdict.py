"""The verdicts of one review (story F9a; S1 `role_value_minimum_sample`; owner, 15 Oct 2026: Holm across a book's
units). The family is fixed: both one-sided claims, "earns its cost" and "drop", of every unit in the registered role
set, so one unit becoming testable never moves another's threshold (as ChatGPT review 120 found for S3). A unit
without a known cost or 30 changed opportunities stays in the family with p = 1. The list goes into S3's Holm
step-down (`fno/scoreboard/uncertainty.py`, imported). A unit passes at most one claim. Nothing is decided without
`--review` on a scheduled review date, and a "drop proposed" is a proposal for the owner, never acted on."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from ..scoreboard.uncertainty import holm
from .score import UnitScore

MIN_CHANGED = 30  # changed opportunities before a unit is judged (S1)
PROVISIONAL = " (provisional: not evidence until F9b's card-withholding test passes)"
DROP, EARNS = "drop proposed, the owner decides" + PROVISIONAL, "earns its cost" + PROVISIONAL
INCONCLUSIVE = "inconclusive, stays"
NOT_REVIEW = "no verdict: not a scheduled review (run with --review on a review date)"
NOT_REVIEW_DATE = "no verdict: {day} is not a scheduled review date"
TOO_FEW = "no verdict: {changed} of 30 changed opportunities"
COST_UNKNOWN = "no verdict: cost unknown"


def _entering(score: UnitScore) -> bool:
    return score.changed >= MIN_CHANGED and score.cost is not None and score.p_earns is not None


def verdicts(scores: Sequence[UnitScore], review: bool, on: date, review_days: Sequence[date]) -> dict[str, str]:
    if not review:
        return {s.unit: NOT_REVIEW for s in scores}
    if on not in review_days:
        return {s.unit: NOT_REVIEW_DATE.format(day=on) for s in scores}
    passed = holm([p for s in scores for p in _claims(s)])
    found = {}
    for i, score in enumerate(scores):
        if not _entering(score):
            found[score.unit] = COST_UNKNOWN if score.cost is None else TOO_FEW.format(changed=score.changed)
            continue
        earns, drop = passed[2 * i], passed[2 * i + 1]
        found[score.unit] = EARNS if earns else DROP if drop else INCONCLUSIVE
    return found


def _claims(score: UnitScore) -> tuple[float, float]:
    """A unit's two one-sided p-values; a unit that cannot be tested at this review stays in the family with p = 1."""
    return (score.p_earns, score.p_drop) if _entering(score) else (1.0, 1.0)
