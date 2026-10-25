"""The results document of one period (story B3): every opportunity with its features and each structure's result,
every policy's and control's metrics, and, for the decisive period only, the controls, bootstraps, criteria and
verdict. Discovery is reported without pass/fail (protocol section 2). Values are unrounded here."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict

from .experiments import Experiment, Period
from .metrics import policy_summary
from .opportunities import Opportunity, actions
from .verdict import ScoredPeriod, overall_verdict, policy_verdict, year_block_bound

DECISIVE_NOTE = (
    "Pre-registered historical holdout on close-proxy data (daily closes), not a 15:00 desk validation and not a "
    "forward test; anything that passes still needs forward paper evidence."
)
REPORTED_NOTE = (
    "Already looked at when the policies were chosen: reported only, never judged. Close-proxy data (daily closes), "
    "not a 15:00 desk validation."
)


def score(experiment: Experiment, opportunities: Sequence[Opportunity], structures: tuple[str, ...]) -> ScoredPeriod:
    chosen = {}
    for spec in experiment.policies:
        chosen[spec.code] = actions(spec.policy, opportunities)
        if spec.opposite is not None:
            chosen[spec.opposite.code] = actions(spec.opposite, opportunities)
    return ScoredPeriod(opportunities, chosen, structures)


def opportunity_rows(opportunities: Sequence[Opportunity]) -> list[dict]:
    return [
        {
            "cycle": {k: v.isoformat() for k, v in asdict(o.cycle).items()},
            "features": dict(o.features),
            "structures": {code: _result_row(o, code) for code in sorted(o.results)},
        }
        for o in opportunities
    ]


def _result_row(opportunity: Opportunity, code: str) -> dict:
    result = opportunity.result(code)
    return {
        "status": opportunity.status(code), "width": result.width, "gross": result.gross, "charges": result.charges,
        "pads": result.pads, "net": result.net, "max_loss": result.max_loss,
        "needs_settlement": result.needs_settlement, "exit_outside_payoff": result.exit_outside_payoff,
    }  # fmt: skip


def period_document(experiment: Experiment, period: Period, scored: ScoredPeriod, ledger_count: dict) -> dict:
    terms = experiment.stats
    policies = {}
    for code, chosen in scored.actions.items():
        policies[code] = {"actions": chosen, "summary": policy_summary(scored.opportunities, chosen, terms.tax_rate)}
    document = {
        "experiment": experiment.folder,
        "period": {"name": period.name, "start": period.start.isoformat(), "end": period.end.isoformat()},
        "decisive": period.decisive,
        "note": DECISIVE_NOTE if period.decisive else REPORTED_NOTE,
        "ledger": ledger_count,
        "opportunities": opportunity_rows(scored.opportunities),
        "policies": policies,
    }
    if period.decisive:
        verdicts = {spec.code: policy_verdict(spec, scored, experiment) for spec in experiment.policies}
        document["overall"] = overall_verdict(verdicts)
        for code, verdict in verdicts.items():
            verdict["criteria"] = [{**asdict(c), "passed": c.passed} for c in verdict["criteria"]]
            verdict["sensitivity"] = {"year_block_lower_bound": year_block_bound(scored, code, experiment)}
            policies[code]["verdict"] = verdict
    return document
