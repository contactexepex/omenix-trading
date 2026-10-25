"""What defines an experiment for the policy runner (story B3): its periods, policies with their controls and
comparisons, the ledger trials, and the statistics terms of its protocol. Each experiment is one data module
(experiment 1: `experiment_1.py`), registered in `EXPERIMENTS` by its research folder name."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from .policies import RulePolicy


@dataclass(frozen=True)
class Period:
    name: str
    start: date  # first decision day included
    end: date  # last decision day included
    decisive: bool  # pass/fail applies (needs the frozen protocol); otherwise results are reported only


@dataclass(frozen=True)
class BranchTest:
    """The P&L of `structure` summed over the opportunities where every (policy code, action) of `where` holds
    (statuses other than traded count 0) must be above zero (`above_zero`) or below zero."""

    name: str
    where: tuple[tuple[str, str | None], ...]
    structure: str
    above_zero: bool


@dataclass(frozen=True)
class PolicySpec:
    policy: RulePolicy
    trial_id: str
    opposite: RulePolicy | None = None  # C2; a conditional policy also gets C1 (random timing)
    compared_with: tuple[str, ...] = ()
    branch_tests: tuple[BranchTest, ...] = ()

    @property
    def code(self) -> str:
        return self.policy.code

    @property
    def conditional(self) -> bool:
        return self.opposite is not None


@dataclass(frozen=True)
class StatisticsTerms:
    seed: int
    resamples: int  # bootstrap resamples (opportunity and year-block)
    lower_bound_index: int  # 0-based index in the ascending resampled means
    control_runs: int  # C1 random-timing sequences
    control_percentile: float  # C1 threshold, nearest rank: index ceil(p x runs) - 1, no interpolation
    mc_repeats: int  # repeat bootstraps (seeds + 1 ...) for the lower bound's Monte Carlo error, reported only
    tax_rate: float  # assumed rate on a positive financial-year net, reported only
    loss_cap: float  # criterion 7: no traded modelled maximum loss above this


@dataclass(frozen=True)
class Experiment:
    folder: str  # research/<folder>/ holds the protocol and the results
    ledger_name: str  # the `experiment` column of research/ledger.csv
    protocol_path: str
    periods: tuple[Period, ...]
    policies: tuple[PolicySpec, ...]
    control_trials: tuple[str, ...]
    stats: StatisticsTerms
    hypotheses: int = field(default=0)  # the multiplicity family declared by the protocol

    def period(self, name: str) -> Period:
        found = next((p for p in self.periods if p.name == name), None)
        if found is None:
            raise ValueError(f"{self.folder} has no period {name!r}: {[p.name for p in self.periods]}")
        return found

    @property
    def trial_ids(self) -> tuple[str, ...]:
        return tuple(spec.trial_id for spec in self.policies) + self.control_trials

    def spec(self, code: str) -> PolicySpec:
        return next(spec for spec in self.policies if spec.code == code)
