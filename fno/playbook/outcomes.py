"""One opportunity's result in story D2's evaluation, with everything a replay compares: the live values seen, the
unmet conditions, the trade built, the risk verdicts, the decision and its reason."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from ..constants import Decision
from ..research_engine.features import FeatureValue
from ..risk.manager import RiskDecision
from .candidates import Candidate
from .opportunities import Opportunity


@dataclass(frozen=True)
class Outcome:
    opportunity: Opportunity
    features: Mapping[str, FeatureValue]
    decision: Decision
    reason: str
    unmet: tuple[str, ...] = ()
    candidate: Candidate | None = None
    risk: RiskDecision | None = None

    def record(self) -> dict:
        strategy, context = self.opportunity.strategy, self.opportunity.context
        return {
            "opportunity_id": self.opportunity.opportunity_id,
            "strategy": strategy.name,
            "version": strategy.version,
            "rule_sha256": strategy.parameters_sha256,
            "mode": self.opportunity.mode,
            "expiry": context.expiry.isoformat(),
            "exit_day": context.exit_day.isoformat(),
            "features": dict(sorted(self.features.items())),
            "unmet_conditions": list(self.unmet),
            "trade": _trade(self.candidate),
            "risk": self.risk.record() if self.risk else None,
            "decision": str(self.decision),
            "reason": self.reason,
        }


def _trade(candidate: Candidate | None) -> dict | None:
    if candidate is None:
        return None
    proposal = candidate.proposal
    return {
        "trade_id": proposal.trade_id,
        "structure": proposal.terms.structure,
        "width": proposal.terms.width,
        "lots": proposal.terms.lots,
        "legs": [
            {"contract": p.contract, "strike": p.leg.strike, "type": p.leg.kind, "side": p.leg.side}
            for p in proposal.legs
        ],
        "max_loss_rs": round(candidate.max_loss, 2),
        "expected_net_rs": candidate.expected_net,
        "score": None if candidate.score is None else round(candidate.score, 6),
    }


@dataclass(frozen=True)
class DayEvaluation:
    day: str
    book: str
    outcomes: tuple[Outcome, ...] = field(default_factory=tuple)

    @property
    def chosen(self) -> tuple[Outcome, ...]:
        return tuple(o for o in self.outcomes if o.decision == Decision.CHOSEN)

    @property
    def eligible(self) -> frozenset[tuple[str, int]]:
        """The book's versions whose rule fired with a valid candidate that its own limits let through to C2 (chosen, or
        not chosen by C2 against the book after the day's other choices), as (name, version): what Book 2's envelope
        may choose among (story D4, criterion 9). A rule that did not fire, or a candidate its own version refused (the
        no-trade threshold, the unproven limit), is never eligible: nothing after D2 re-checks those (judge 260
        addendum 1), while C2's own refusals are re-checked for the chosen trade (its verdicts, then C4)."""
        valid = (Decision.CHOSEN, Decision.NOT_CHOSEN)
        reached_c2 = (o for o in self.outcomes if o.decision in valid and o.risk is not None)
        return frozenset(o.opportunity.strategy.key for o in reached_c2)

    def record(self) -> dict:
        chosen = [o.opportunity.opportunity_id for o in self.chosen]
        return {
            "day": self.day,
            "book": self.book,
            "decision": "trade" if chosen else "no trade",
            "chosen": chosen,
            "outcomes": [o.record() for o in self.outcomes],
        }
