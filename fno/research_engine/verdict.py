"""Pass/fail exactly as experiment 1's protocol section 8 says (story B3): each criterion a separate true/false with
its value and threshold, computed on unrounded numbers; a policy passes only if every criterion that applies to it
holds. Criterion 7 (no traded modelled maximum loss above the cap) failing makes the whole run void."""

from __future__ import annotations

import operator
from collections.abc import Sequence
from dataclasses import dataclass

from .controls import random_timing_totals
from .experiments import BranchTest, Experiment, PolicySpec
from .opportunities import Action, Opportunity, pnl_series
from .statistics import lower_bound, monte_carlo_error, nearest_rank, year_block_lower_bound

RULES = {">": operator.gt, "<": operator.lt, "<=": operator.le}
VERDICT_PASS, VERDICT_FAIL, VERDICT_VOID = "pass", "fail", "void"


@dataclass(frozen=True)
class Criterion:
    name: str
    value: float
    rule: str  # value <rule> threshold must hold
    threshold: float

    @property
    def passed(self) -> bool:
        return RULES[self.rule](self.value, self.threshold)


@dataclass(frozen=True)
class ScoredPeriod:
    """The period's opportunities and every policy's and control's actions, by code."""

    opportunities: Sequence[Opportunity]
    actions: dict[str, list[Action]]
    structures: tuple[str, ...]

    def pnl(self, code: str) -> list[float]:
        return pnl_series(self.opportunities, self.actions[code])

    def total(self, code: str) -> float:
        return sum(self.pnl(code))

    def structure_pnl(self, structure: str) -> list[float]:
        return [o.pnl(structure) for o in self.opportunities]


def branch_sum(test: BranchTest, scored: ScoredPeriod) -> float:
    rows = range(len(scored.opportunities))
    hits = [i for i in rows if all(scored.actions[code][i] == action for code, action in test.where)]
    return sum(scored.opportunities[i].pnl(test.structure) for i in hits)


def largest_traded_loss(scored: ScoredPeriod, code: str) -> float:
    losses = [
        o.result(a).max_loss for o, a in zip(scored.opportunities, scored.actions[code], strict=True) if o.traded(a)
    ]
    return max(losses, default=0.0)


def policy_verdict(spec: PolicySpec, scored: ScoredPeriod, experiment: Experiment) -> dict:
    terms, code = experiment.stats, spec.code
    pnl, total = scored.pnl(code), scored.total(code)
    bound = lower_bound(pnl, terms)
    criteria = [Criterion("1_total_net", total, ">", 0.0), Criterion("2_bootstrap_lower_bound", bound, ">", 0.0)]
    details = {"lower_bound": bound, "lower_bound_mc_error": monte_carlo_error(pnl, terms)}
    if spec.conditional:
        by_structure = {s: scored.structure_pnl(s) for s in scored.structures}
        runs = random_timing_totals(scored.actions[code], by_structure, terms.control_runs, terms.seed)
        details["c1_threshold"] = nearest_rank(runs, terms.control_percentile)
        details["c2_total_net"] = scored.total(spec.opposite.code)
        criteria += [
            Criterion("3_above_random_timing", total, ">", details["c1_threshold"]),
            Criterion("3_above_opposite", total, ">", details["c2_total_net"]),
        ]
    criteria += [Criterion(f"4_above_{other}", total, ">", scored.total(other)) for other in spec.compared_with]
    criteria += [
        Criterion(f"{5 if t.above_zero else 6}_{t.name}", branch_sum(t, scored), ">" if t.above_zero else "<", 0.0)
        for t in spec.branch_tests
    ]
    criteria.append(Criterion("7_max_modelled_loss", largest_traded_loss(scored, code), "<=", terms.loss_cap))
    passed = all(c.passed for c in criteria)
    return {"criteria": criteria, "details": details, "verdict": VERDICT_PASS if passed else VERDICT_FAIL}


def year_block_bound(scored: ScoredPeriod, code: str, experiment: Experiment) -> float:
    """Sensitivity (never used to pass): the lower bound when whole calendar years (of the exit day) are resampled."""
    years: dict[int, list[float]] = {}
    for opportunity, value in zip(scored.opportunities, scored.pnl(code), strict=True):
        years.setdefault(opportunity.cycle.exit_day.year, []).append(value)
    return year_block_lower_bound([years[y] for y in sorted(years)], experiment.stats)


def overall_verdict(verdicts: dict[str, dict]) -> dict:
    """Void if any policy broke criterion 7 (the run is investigated, nothing passes); else the policies that passed
    every criterion that applies to them."""
    void = any(not c.passed for v in verdicts.values() for c in v["criteria"] if c.name.startswith("7_"))
    passing = [] if void else [code for code, v in verdicts.items() if v["verdict"] == VERDICT_PASS]
    return {"status": VERDICT_VOID if void else "complete", "passing_policies": passing}
