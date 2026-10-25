"""The whole-project stop rule's decision unit (design v2 section 8.2, frozen with v4; PROTOCOL_v4.md section 6).

Test A counts only the registered family's members whose slot has a registered forecaster at the review (G1 v3 is
reported beside it, never counted). Test B counts only shadow strategies registered in the ledger before the review.
Each test has three results, never two: underpowered is never "no", and no observations give no bound.
"""

from __future__ import annotations

from collections.abc import Sequence, Set
from dataclasses import dataclass

from ..constants import (
    CONTINUE,
    CONTINUE_HALF_AI_BUDGET,
    STOP_NO,
    STOP_NO_ECONOMIC_TEST,
    STOP_OR_PIVOT,
    STOP_UNDECIDED,
    STOP_YES,
    UNDECIDED_OPTION_1,
    UNDECIDED_OPTION_2,
    V4_CLAIM,
)
from .family import MemberVerdict
from .terms import DESCRIPTIVE_ONLY, USEFUL_TIME_YEARS


@dataclass(frozen=True)
class ShadowResult:
    """A counted shadow strategy at the review: its one-sided 95% bounds of net per trade after costs (None with no
    resolved trade), whether it reached its registered sample, and its registered minimum useful net per trade."""

    lower_bound: float | None
    upper_bound: float | None
    reached_sample: bool
    min_useful_net: float


def forecasting_test(members: Sequence[MemberVerdict], registered: Set[tuple[str, str]]) -> str:
    """yes: a counted member claims (calibrated rule and the minimum effect). no: every counted member is futile, a
    significant but too-small one included. Else undecided, including when nothing is counted. Descriptive-only
    members (V7) are never counted: they can neither claim nor block a "no"."""
    counted = [m for m in members if (m.question, m.slot) in registered and m.question not in DESCRIPTIVE_ONLY]
    if any(m.verdict == V4_CLAIM for m in counted):
        return STOP_YES
    if counted and all(m.futile for m in counted):
        return STOP_NO
    return STOP_UNDECIDED


def money_test(shadows: Sequence[ShadowResult]) -> str:
    """yes: a lower bound above zero. no: every shadow reached its sample with its upper bound below its minimum
    useful net. Zero counted shadows: undecided / no_economic_test, never "no"."""
    if not shadows:
        return STOP_NO_ECONOMIC_TEST
    if any(s.lower_bound is not None and s.lower_bound > 0 for s in shadows):
        return STOP_YES
    if all(s.reached_sample and s.upper_bound is not None and s.upper_bound < s.min_useful_net for s in shadows):
        return STOP_NO
    return STOP_UNDECIDED


def review_outcome(a: str, b: str, settle_years_after_review: float | None) -> str:
    """Both tests must say no to stop or pivot. "Undecided" takes the owner's choice recorded before any v4 score:
    option 1 when the best-powered question's projected settle date is at most 2 years after the review, option 2
    when it is later or cannot be projected (no question reached its 60-outcome power report)."""
    if b == STOP_YES:
        return CONTINUE
    if a == STOP_NO and b == STOP_NO:
        return STOP_OR_PIVOT
    if a == STOP_YES:
        return CONTINUE_HALF_AI_BUDGET
    if settle_years_after_review is not None and settle_years_after_review <= USEFUL_TIME_YEARS:
        return UNDECIDED_OPTION_1
    return UNDECIDED_OPTION_2
