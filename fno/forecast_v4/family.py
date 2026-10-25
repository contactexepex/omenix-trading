"""The confirmatory family of protocol v4 (PROTOCOL_v4.md section 5): Bonferroni at Holm's first step (rate / 15) over
the 15 registered members at each of at most two looks, with p = 1 for every member not judged at that look (ChatGPT
review 98's caveat). Revision 2 (rule E+D) calibrated only the first step's critical values, so the later Holm steps
are not used; a member's p is its calibrated p (`confirmatory.calibrated_p`).

A member is judged at a look only when its slot has a registered forecaster, it has at least 2L scored pairs and it was
not closed earlier (a claim or a futility "no" at look 1 is final). Every decision states the look, its family-wise
rate, its timestamp and all 15 members, judged or not.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime

from ..constants import V4_CLAIM, V4_FUTILE, V4_OPEN, V4_TOO_SMALL
from .terms import DESCRIPTIVE_ONLY, FAMILY, LOOK_ERROR_RATE

NOT_JUDGED_P = 1.0


@dataclass(frozen=True)
class MemberResult:
    """One member's statistics at a look. `p_value` is its calibrated p; None: not judged at this look (no registered
    forecaster, fewer than 12 batches, or closed at an earlier look)."""

    p_value: float | None
    meets_minimum_effect: bool
    futile: bool


@dataclass(frozen=True)
class MemberVerdict:
    question: str
    slot: str
    judged: bool
    p_used: float  # the calibrated p the family saw: NOT_JUDGED_P when not judged
    significant: bool  # calibrated p at or below rate / 15
    futile: bool  # judged, and the upper bound of its improvement is below the minimum effect
    verdict: str  # V4_CLAIM, V4_TOO_SMALL (significant, below the effect), V4_FUTILE or V4_OPEN


@dataclass(frozen=True)
class FamilyDecision:
    look: str
    error_rate: float
    decided_at: datetime
    members: tuple[MemberVerdict, ...]  # all of FAMILY, in its order

    def header(self) -> str:
        judged = sum(m.judged for m in self.members)
        return (
            f"protocol v4 family: {len(self.members)} members, {judged} judged, "
            f"{len(self.members) - judged} at p = 1; "
            f"look {self.look} at family-wise {self.error_rate:g}; decided at {self.decided_at.isoformat()}"
        )

    def lines(self) -> list[str]:
        """The header, then every member (judged or not): what each report prints, so membership is never implied."""
        rows = [
            f"{m.question} {m.slot}: p {m.p_used:.4f}{'' if m.judged else ' (not judged)'}, {m.verdict}"
            for m in self.members
        ]
        return [self.header(), *rows]


def bonferroni(p_values: Sequence[float], rate: float) -> list[bool]:
    """Each p against rate / m: the union bound holds the family-wise rate whatever the dependence between members."""
    return [p <= rate / len(p_values) for p in p_values]


def judge_family(look: str, decided_at: datetime, results: Mapping[tuple[str, str], MemberResult]) -> FamilyDecision:
    """Every member of FAMILY is in the decision; a member missing from `results`, or a descriptive-only one (V7), is
    not judged (p = 1)."""
    if decided_at.tzinfo is None:
        raise ValueError("a decision timestamp needs its time zone")
    unknown = set(results) - set(FAMILY)
    if unknown:
        raise ValueError(f"not members of the registered family: {sorted(unknown)}")
    rate = LOOK_ERROR_RATE[look]
    stats = [None if member[0] in DESCRIPTIVE_ONLY else results.get(member) for member in FAMILY]
    p_used = [s.p_value if s is not None and s.p_value is not None else NOT_JUDGED_P for s in stats]
    significant = bonferroni(p_used, rate)
    members = tuple(
        _verdict(member, stat, p, sig) for member, stat, p, sig in zip(FAMILY, stats, p_used, significant, strict=True)
    )
    return FamilyDecision(look, rate, decided_at, members)


def _verdict(member: tuple[str, str], stat: MemberResult | None, p: float, significant: bool) -> MemberVerdict:
    judged = stat is not None and stat.p_value is not None
    if judged and significant:
        verdict = V4_CLAIM if stat.meets_minimum_effect else V4_TOO_SMALL
    elif judged and stat.futile:
        verdict = V4_FUTILE
    else:
        verdict = V4_OPEN
    return MemberVerdict(member[0], member[1], judged, p, judged and significant, judged and stat.futile, verdict)
