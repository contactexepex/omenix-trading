"""A fired opportunity's trade built on the day's live quotes (story D2): the structure code fixes the body strikes,
each width of the version is tried widest first, and the widest whose maximum loss (every charge and pad, C2's cost
model) is within the per-trade cap is kept. A width whose prices put the position at or beyond its payoff bounds (a
trade that cannot lose or cannot win) is skipped like an unlisted one, exactly as the research did (experiment 1
protocol "Impossible prices", `simulator._entry_trial`; judge 69), so the desk trades what was tested. The score is the
version's frozen expected net per opportunity divided by that maximum loss. Prices come only from valid quotes in the
market given; nothing is invented."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date

from ..research_engine.structures import Chain, Structure, payoff_bounds, position_value
from ..risk.inputs import Market, Proposal, ProposedLeg, RiskInputError, TradeTerms
from ..risk.trade_costs import TradeCosts
from .opportunities import Opportunity


@dataclass(frozen=True)
class Candidate:
    opportunity: Opportunity
    proposal: Proposal
    max_loss: float
    expected_net: float | None  # None: a research version without an honest estimate (shadow only)

    @property
    def score(self) -> float | None:
        """Expected net per rupee of maximum loss (D2's ranking); None without an estimate."""
        return None if self.expected_net is None else self.expected_net / self.max_loss

    def rank_key(self) -> tuple:
        """Higher score first (no estimate last); ties: lower maximum loss, earlier expiry, then name and version."""
        strategy, score = self.opportunity.strategy, self.score
        return (
            score is None,
            -(score or 0.0),
            self.max_loss,
            self.opportunity.context.expiry,
            strategy.name,
            strategy.version,
        )


class NotBuilt(ValueError):
    """The opportunity has no tradable structure today; the reason says why (no trade)."""


def live_chain(market: Market, expiry: date) -> dict[tuple[float, str], str]:
    """(strike, type) -> contract symbol for the expiry's contracts with a valid (not stale) quote."""
    return {(q.strike, q.kind): c for c, q in sorted(market.quotes.items()) if q.expiry == expiry and not q.stale}


class CandidateBuilder:
    def __init__(self, structures: Mapping[str, Structure], costs: TradeCosts, max_loss_cap: float, lot_size: int):
        self.structures, self.costs, self.cap, self.lot_size = dict(structures), costs, max_loss_cap, lot_size

    def build(self, opportunity: Opportunity, market: Market, trade_id: str) -> Candidate:
        spec = opportunity.strategy.structure
        contracts = live_chain(market, opportunity.context.expiry)
        chain: Chain = frozenset(contracts)
        tried = []
        for width in spec.widths:
            legs = self.structures[spec.code].legs(chain, market.spot, width)
            if legs is None:
                tried.append(f"{width:g}: not listed with valid quotes")
                continue
            proposed = tuple(ProposedLeg(contracts[leg.contract], leg) for leg in legs)
            proposal = Proposal(trade_id, TradeTerms(spec.code, width, spec.lots), self.lot_size, proposed)
            try:
                prices = proposal.entry_prices(market)
                max_loss = self.costs.max_loss(proposal, market)
            except RiskInputError as problem:
                tried.append(f"{width:g}: {problem}")
                continue
            lowest, highest = payoff_bounds(legs)
            if not lowest < position_value(legs, prices) < highest:
                tried.append(f"{width:g}: bad prices (the position cannot lose or cannot win at expiry)")
                continue
            if max_loss <= self.cap:
                expected = opportunity.strategy.evaluation_plan["expected_net_per_opportunity"]
                return Candidate(opportunity, proposal, max_loss, expected)
            tried.append(f"{width:g}: maximum loss {max_loss:.2f} above the cap {self.cap:g}")
        raise NotBuilt("no width tradable: " + "; ".join(tried))
