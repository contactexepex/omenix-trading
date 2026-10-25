"""One opportunity per monthly expiry (story B3, protocol sections 3 and 7): the cycle, its decision-day features and
every structure's simulated result, so each policy and control is scored on exactly the same opportunities. A policy's
per-opportunity P&L is the chosen structure's net if it traded, else 0 (no trade and every other status count 0)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from ..constants import NO_TRADE, CycleStatus
from .cycles import Cycle
from .features import DecisionContext, Feature, FeatureValue, ResearchData
from .policies import Policy
from .simulator import CycleResult, CycleSimulator
from .structures import Structure

Action = str | None  # a structure code, or None for no trade


def checked_status(status: object) -> str:
    """B2's statuses, exactly: any other value is an error, never a silent zero (story B2 design)."""
    if not isinstance(status, CycleStatus):
        raise ValueError(f"unknown cycle status {status!r}: B3 consumes exactly {[s.value for s in CycleStatus]}")
    return status.value


@dataclass(frozen=True)
class Opportunity:
    cycle: Cycle
    features: Mapping[str, FeatureValue]
    results: Mapping[str, CycleResult]  # structure code -> the structure's result in this cycle

    def result(self, action: str) -> CycleResult:
        return self.results[action]

    def status(self, action: Action) -> str:
        return NO_TRADE if action is None else checked_status(self.result(action).status)

    def traded(self, action: Action) -> bool:
        return action is not None and self.result(action).status == CycleStatus.TRADED

    def pnl(self, action: Action) -> float:
        return self.result(action).net if self.traded(action) else 0.0

    def no_settlement_pnl(self, action: Action) -> float:
        return self.result(action).no_settlement_net if self.traded(action) else 0.0

    def exit_outside_payoff(self, action: Action) -> bool:
        """A traded exit valued beyond what the position can pay at expiry (B2's report-only flag)."""
        return self.traded(action) and self.result(action).exit_outside_payoff


def build_opportunities(
    cycles: Sequence[Cycle],
    data: ResearchData,
    features: Sequence[Feature],
    structures: Sequence[Structure],
    simulator: CycleSimulator,
) -> list[Opportunity]:
    opportunities = []
    for cycle in cycles:
        context = DecisionContext(cycle.expiry, cycle.entry_day, cycle.exit_day)
        values = {f.name: f.value(data, cycle.decision_day, context) for f in features}
        results = {s.code: simulator.simulate(cycle, s) for s in structures}
        opportunities.append(Opportunity(cycle, values, results))
    return opportunities


def actions(policy: Policy, opportunities: Sequence[Opportunity]) -> list[Action]:
    return [policy.decide(o.features) for o in opportunities]


def pnl_series(opportunities: Sequence[Opportunity], chosen: Sequence[Action]) -> list[float]:
    return [o.pnl(a) for o, a in zip(opportunities, chosen, strict=True)]
