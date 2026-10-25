"""A confirmatory look of protocol v4 (sections 5-6; story G8): each registered member judged by the frozen rules, the
family decision, Test A, and every member's scored-window regime. A member is judged only when its window passes both
gates, the 5 2%-day gate (`judgeable`) and the owner's crash-share cut (`crash_dominated`), has at least 12 whole
batches, was not closed at look 1 (a claim or a futility "no" is final) and is not "undecided, operations" (too many
missed days, revision 9: never a claim, never futile, so Test A stays undecided)."""

from __future__ import annotations

from collections.abc import Mapping, Set
from dataclasses import dataclass
from datetime import datetime

from ...forecast_v4.bootstrap import effect_check
from ...forecast_v4.confirmatory import (
    FUTILITY_LEVEL,
    MIN_CLAIM_BATCHES,
    calibrated_p,
    crash_dominated,
    event_band,
    futility_p,
    judgeable,
)
from ...forecast_v4.family import FamilyDecision, MemberResult, judge_family
from ...forecast_v4.stop_rule import forecasting_test
from ...forecast_v4.terms import BLOCK_LENGTH, DESCRIPTIVE_ONLY, FAMILY, FAMILY_SIZE, LOOK_ERROR_RATE, family_seed_word
from .comparison import Comparison, margin
from .thresholds import ThresholdSource

NOT_JUDGED = MemberResult(None, False, False)
NO_WINDOW = "no scored window"


@dataclass(frozen=True)
class LookResult:
    decision: FamilyDecision
    test_a: str
    regimes: dict[tuple[str, str], str]  # each member's regime line (or NO_WINDOW)
    misses: dict[tuple[str, str], str]  # each member's miss line (revision 9)

    def lines(self) -> list[str]:
        header, *members = self.decision.lines()
        out = [header]
        for member, row in zip(FAMILY, members, strict=True):
            out += [row, f"  {self.regimes.get(member, NO_WINDOW)}"]
            if member in self.misses:
                out.append(f"  {self.misses[member]}")
        return out + [f"Test A (forecasting): {self.test_a}"]


def member_result(comparison: Comparison, look: str, thresholds: ThresholdSource, k: int) -> MemberResult:
    scored, gate = comparison.pairing.scored, comparison.pairing.gate
    question, block = comparison.question, BLOCK_LENGTH[comparison.question]
    regime = comparison.regime
    if question in DESCRIPTIVE_ONLY:  # V7: never judged, and no threshold tool covers it (judge 128 addendum 1)
        return NOT_JUDGED
    if comparison.misses.operations_undecided:
        return NOT_JUDGED
    if regime is None or len(scored.differences) // block < MIN_CLAIM_BATCHES:
        return NOT_JUDGED
    if not judgeable(regime.big_days) or crash_dominated(regime.big_days, len(scored.differences)):
        return NOT_JUDGED
    found = thresholds.thresholds(question, look, len(scored.differences), len(gate.differences), event_band(
        regime.big_days))  # fmt: skip
    p = calibrated_p(scored.differences, block, found.claim, LOOK_ERROR_RATE[look] / FAMILY_SIZE)
    meets = effect_check(gate, margin(question), block, k, look).meets_minimum_effect
    futile = futility_p(gate.differences, gate.baseline_losses, block, margin(question), found.futility)
    return MemberResult(p, meets, futile <= FUTILITY_LEVEL)


def run_look(look: str, decided_at: datetime, members: Mapping[tuple[str, str], Comparison],
             thresholds: ThresholdSource, closed: Set[tuple[str, str]]) -> LookResult:  # fmt: skip
    """`members`: each registered member's comparison (its slot's forecaster against the primary baseline);
    `closed`: members closed at look 1."""
    results = {
        member: NOT_JUDGED
        if member in closed
        else member_result(comparison, look, thresholds, family_seed_word(*member))
        for member, comparison in members.items()
    }
    decision = judge_family(look, decided_at, results)
    regimes = {m: c.regime.line() if c.regime else NO_WINDOW for m, c in members.items()}
    misses = {m: c.misses.line() for m, c in members.items()}
    return LookResult(decision, forecasting_test(decision.members, set(members)), regimes, misses)
