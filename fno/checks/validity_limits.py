"""The owner's account limits as C4 recomputes them (stories C4 and C5, judge 83): exactly the rules the risk profile
lists, as C2 runs them. The books: paper account, bucket, open-risk and new-risk caps, drawdown brake and margin room;
the Manual account: paper account, open trades, drawdown brake, stress, exposure and margin room. Each is computed
from raw inputs:
- the book's ledger, as C4 reads it;
- the committed snapshot, priced by C4's own model;
- A14's margins file.

The book's trades chosen earlier the same day (those that passed C4) count as entered, as D2 counts them. A leg C4
cannot price, or an account or margin it cannot read, fails the check that needs it."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace

from .validity_account import AccountFacts, Position
from .validity_caps import CapChecks, CapProblem, Exposure, buckets_of, paper_account_check
from .validity_chain import PricedChain
from .validity_drawdown import drawdown_check
from .validity_evidence import Evidence
from .validity_margin import MarginProblem, margin_check
from .validity_money import entry_cash_flow, max_loss
from .validity_pricing import PricingProblem
from .validity_proposal import CheckResult, ValidityProposal
from .validity_settings import ValidityLimits
from .validity_stress import StressChecks

PRICED_ORDER = ("bucket_cap", "open_risk_cap", "new_risk_per_day", "stress_loss", "exposure_limit", "margin_room")
CAP_RULES = PRICED_ORDER[:3]


def priced(rules) -> tuple[str, ...]:
    """The profile's checks that need the snapshot's prices, in report order."""
    return tuple(name for name in PRICED_ORDER if name in rules or name == "margin_room")


def position_of(proposal: ValidityProposal, charges: Mapping[str, float]) -> Position:
    legs = [leg.leg for leg in proposal.legs]
    units = {leg.contract: leg.leg.side * proposal.units for leg in proposal.legs}
    return Position(proposal.opportunity_id, units, entry_cash_flow(legs, proposal.units, charges), proposal.terms)


class LimitChecks:
    def __init__(self, limits: ValidityLimits, charges: Mapping[str, float], margins):
        self.limits, self.charges, self.margins = limits, dict(charges), margins

    def held(self, proposal: ValidityProposal, account: AccountFacts) -> AccountFacts:
        """The account with its open trades' recorded terms, after the trades chosen earlier the same day."""
        terms = proposal.open_terms
        opened = tuple(replace(p, terms=terms.get(p.trade_id)) for p in account.positions)
        account = replace(account, positions=opened)
        for earlier in proposal.earlier:
            account = account.after_entry(position_of(earlier, self.charges))
        return account

    def checks(self, proposal: ValidityProposal, account: AccountFacts, evidence: Evidence | None) -> list[CheckResult]:
        limits, opened = self.limits, account
        account = self.held(proposal, account)
        results = [paper_account_check(opened, limits.paper_account)]
        if "max_open_trades" in limits.rules:
            count, limit = len(account.positions), limits.max_open_trades
            reason = f"{count} open or chosen before, limit {limit}"
            results.append(CheckResult("open_trades", count + 1 <= limit, reason))
        results.append(drawdown_check(account, limits.drawdown_brake))
        if evidence is None:
            unpriced = priced(limits.rules)
            return results + [CheckResult(name, False, "no trusted snapshot to price with") for name in unpriced]
        return results + self._priced(proposal, account, PricedChain(evidence, proposal.day, limits.rate))

    def _caps(self, proposal: ValidityProposal, account: AccountFacts, chain: PricedChain) -> list[CheckResult]:
        names = [name for name in CAP_RULES if name in self.limits.rules]
        if not names:
            return []
        try:
            legs = [leg.leg for leg in proposal.legs]
            buckets = buckets_of(proposal.structure, [leg.contract for leg in proposal.legs], self.limits.caps.sides)
            own = Exposure(proposal.opportunity_id, buckets, max_loss(legs, proposal.units, self.charges).total)
            checks = CapChecks(self.limits.caps, names, self.charges)
            return checks.checks(account.positions, account.session, own, chain)
        except (CapProblem, PricingProblem) as problem:
            return [CheckResult(name, False, str(problem)) for name in names]

    def _priced(self, proposal: ValidityProposal, account: AccountFacts, chain: PricedChain) -> list[CheckResult]:
        own, held, rules = position_of(proposal, self.charges), account.positions, self.limits.rules
        stress = StressChecks(chain, self.limits, proposal.day)
        checks = [
            ("stress_loss", lambda: stress.stress(held, own)),
            ("exposure_limit", lambda: stress.exposure((*held, own))),
            ("margin_room", lambda: margin_check(held, own, account.cash, proposal.premium_reserved, chain,
                                                 self.margins.rows(), self.limits.margins, proposal.day,
                                                 proposal.lot_size)),
        ]  # fmt: skip
        run = [_run(name, check) for name, check in checks if name in rules or name == "margin_room"]
        return self._caps(proposal, account, chain) + run


def _run(name: str, check) -> CheckResult:
    try:
        return check()
    except (PricingProblem, MarginProblem) as problem:
        return CheckResult(name, False, str(problem))
