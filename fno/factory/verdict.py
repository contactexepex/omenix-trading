"""G6 for a registered shadow (story R1c, FACTORY_RULES section 3 rules 3-5): judged once, at its frozen sample, by
Holm across the cumulative family of its research question.

The family is every shadow ever registered (G4) on the question; only positions opened after a shadow's freeze day
count (FACTORY_RULES section 3, rule 1). Each member's p is a one-sided t test (mean net per
completed position above zero, Student t with n - 1 degrees of freedom) on its first n positions, n its frozen
sample. A member short of n, stopped or retired before it, enters with p = 1. A measurement is never registered (G4
refuses it), so it is never in a family. A trial whose G2 data spend was `exploratory` stays in its family but never
passes (section 4): it is logged failed with exploratory=yes. A verdict is logged once and never relabelled."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from statistics import mean, stdev
from typing import Protocol

from ..books.paths import shadow_account
from ..forecast_v4.student_t import t_cdf
from ..research_engine.ledger import Ledger
from ..scoreboard.uncertainty import holm
from .card import IdeaCard
from .constants import Gate, Outcome
from .gate_log import GateRow, figures
from .gate_order import GateOrder, GateStepError
from .questions import Questions


class ShadowResults(Protocol):
    def nets(self, account: str, opened_after: date) -> list[float]:
        """Net after costs of each completed position of a shadow account opened after `opened_after` (its freeze
        day), oldest first. Open trades never count; neither do records made before the freeze (rule 1)."""


def one_sided_p(nets: list[float]) -> float:
    """P(T >= t) for H0 "mean net per trade <= 0"."""
    if len(nets) < 2:
        return 1.0
    spread = stdev(nets)
    if spread == 0:
        return 0.0 if mean(nets) > 0 else 1.0
    t = mean(nets) / (spread / math.sqrt(len(nets)))
    return 1 - t_cdf(t, len(nets) - 1)


@dataclass(frozen=True)
class Member:
    trial_id: str
    version: str
    sample: int
    positions: int  # completed positions opened after the freeze day
    p: float
    opened_after: str  # the freeze day (its G4 row)


@dataclass(frozen=True)
class FamilyVerdict:
    question_id: str
    alpha: float
    members: tuple[Member, ...]
    judged: Member
    holm_passed: bool  # what Holm says across the family
    exploratory: bool  # its G2 data spend was exploratory: it can never pass

    @property
    def passed(self) -> bool:
        return self.holm_passed and not self.exploratory


class ShadowVerdicts:
    def __init__(self, order: GateOrder, ledger: Ledger, questions: Questions, results: ShadowResults):
        self.order, self.ledger, self.questions, self.results = order, ledger, questions, results

    def judge(self, card: IdeaCard, today: date) -> FamilyVerdict:
        self.order.ready(card, Gate.REGISTRATION, (Outcome.REGISTERED,))
        self.ledger.require_registered(card.trial_id)  # B4: frozen protocol committed and unchanged
        mine = figures(self.order.row(card.trial_id, Gate.REGISTRATION))
        question = self.questions.get(mine["question"])
        family = [self._member(row) for row in self.order.gates.of_gate(Gate.REGISTRATION)
                  if figures(row)["question"] == question.question_id]  # fmt: skip
        judged = next(m for m in family if m.trial_id == card.trial_id)
        if judged.positions < judged.sample:
            raise GateStepError(f"{judged.version}: {judged.positions} of {judged.sample} positions, not at its frozen "
                                "sample: judged only when it gets there")  # fmt: skip
        passes = holm([m.p for m in family], question.alpha)
        exploratory = self.order.row(card.trial_id, Gate.DATA_SPEND).outcome == Outcome.EXPLORATORY
        verdict = FamilyVerdict(question.question_id, question.alpha, tuple(family), judged,
                                passes[family.index(judged)], exploratory)  # fmt: skip
        numbers = (f"p={judged.p:.6f};family={len(family)};alpha={question.alpha:g};question={question.question_id};"
                   f"opened_after={judged.opened_after};exploratory={'yes' if exploratory else 'no'}")  # fmt: skip
        self.order.log(card, Gate.VERDICT, Outcome.PASSED if verdict.passed else Outcome.FAILED, today, numbers)
        return verdict

    def _member(self, row: GateRow) -> Member:
        numbers = figures(row)
        sample = int(numbers["sample"])
        nets = self.results.nets(shadow_account(numbers["version"]), date.fromisoformat(row.on))
        p = one_sided_p(nets[:sample]) if len(nets) >= sample else 1.0
        return Member(row.trial_id, numbers["version"], sample, len(nets), p, row.on)
