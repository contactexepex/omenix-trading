"""C4's Book 3 mode (story D5 criteria 1-4): the trade's strategy must be registered and committed before the decision
and proposed on an earlier session, its spec unchanged, the constitution in force the one D6 registered, the spec and
the trade within that constitution, and the trade the registered spec's own structure, width, lots and shape (the
playbook mode's checks against the spec). C4 is checked before the decision is committed, so "committed at HEAD" here
means strictly before the decision's commit; D6 repeats the strict check when the decision is scored. Red-team and
judge objections are not an input: they can never block a Book 3 trade (design 12.3)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import date, timedelta

from ..book3.constitution import COMPONENT, Constitution, ConstitutionError
from ..book3.registry import NotRegistered, StrategyRegistry
from ..book3.spec_rules import constitution_problems
from ..research_engine.ledger import GitFailed
from .validity_envelope import RegisteredComponents
from .validity_evidence import Evidence
from .validity_modes import PlaybookMode, ValidityMode
from .validity_proposal import CheckResult, ValidityProposal
from .validity_shapes import Shape


class ConstitutionMode(ValidityMode):
    name = "constitution"

    def __init__(self, shapes: dict[str, Shape], constitutions: Callable[[], dict[str, Constitution]],
                 registered: RegisteredComponents, registry: StrategyRegistry, head: Callable[[], str]):  # fmt: skip
        self.playbook = PlaybookMode(shapes)
        self.constitutions, self.registered, self.registry, self.head = constitutions, registered, registry, head

    def checks(self, proposal: ValidityProposal, evidence: Evidence | None) -> list[CheckResult]:
        sha = self.registered(proposal.book, proposal.day).get(COMPONENT, "")
        try:
            constitution = self.constitutions().get(sha)
        except ConstitutionError as damaged:
            return [CheckResult("constitution", False, f"damaged constitution file: {damaged}")]
        if constitution is None:
            return [CheckResult("constitution", False, "no constitution file matches the registered D6 component")]
        try:
            spec = self.registry.require_registered(proposal.strategy_id, proposal.day, self.head())
        except NotRegistered as missing:
            return [CheckResult("constitution", False, str(missing))]
        except GitFailed as failed:  # fails closed by name, never an exception out of C4 (judges 260/263, D5 builder)
            return [CheckResult("constitution", False, f"git failed: {failed}")]
        problems = constitution_problems(spec, constitution) + _holding_problem(proposal, spec, constitution)
        own = replace(proposal, strategy=spec, approved=frozenset({spec.key}))
        within = CheckResult("constitution", not problems, "; ".join(problems) or f"{proposal.strategy_id} registered")
        return [within, *self.playbook.checks(own, evidence)]


def _holding_problem(proposal: ValidityProposal, spec, constitution: Constitution) -> list[str]:
    exit_day = date.fromisoformat(proposal.expiry) - timedelta(days=spec.structure.expiry.exit_days_before_expiry)
    held = (exit_day - proposal.day).days
    return [] if held <= constitution.max_holding_days else [f"planned exit {exit_day} is {held} days after entry"]
