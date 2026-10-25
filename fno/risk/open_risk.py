"""Each position's maximum loss and bucket, the numbers C5's caps add up (design 6.1a, kind 1: the terminal-payoff loss
plus charges, fixed at entry).

A proposal's maximum loss is B2's model, the same number `MaxLossPerTrade` checks. An open trade's is the same model
applied to what the ledger holds: the cash it has moved so far (padded fills and entry charges, E1) plus its worst
value at expiry, plus each leg's exit pad and exit charges at that level (where several levels give the worst value,
the one with the larger exit charges, as B2). For a trade just entered at the modelled fills the two agree (tested).
Its extremes lie at strikes only when neither tail is net short; a held position with more calls or more puts sold than
bought is not defined risk and is refused, never measured. A position that can no longer lose counts as zero, never as
room for another trade. A session trade's new risk is the largest maximum loss it carried after any fill time that day.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from ..constants import OPTION_CALL, OPTION_PUT
from ..research_engine.cycle_costs import PAD, CycleTerms, PositionCosts
from ..research_engine.structures import BOUGHT, SOLD, Leg
from .buckets import Bucket, BucketMap
from .inputs import Market, OpenTrade, Proposal, RiskInputError, SessionTrade
from .trade_costs import TradeCosts


@dataclass(frozen=True)
class PositionRisk:
    trade_id: str
    buckets: tuple[Bucket, ...]  # one per side of its structure (a directional spread has two)
    max_loss_rs: float


class HeldMaxLoss:
    """B2's maximum loss of a held position, from its signed units and its cash flow so far."""

    def __init__(self, charges: Mapping[str, float], pad: float = PAD):
        self.charges, self.pad = dict(charges), pad

    def _legs(self, units: Mapping[str, int], market: Market) -> list[tuple[Leg, int]]:
        legs = []
        for contract, count in units.items():
            quote = market.quote(contract)
            legs.append((Leg(quote.strike, quote.kind, BOUGHT if count > 0 else SOLD), abs(count)))
        return legs

    def _exit_charges(self, legs: list[tuple[Leg, int]], level: float) -> float:
        return sum(
            PositionCosts(CycleTerms(lot=n, charges=self.charges, pad=self.pad)).leg_charges(
                leg, leg.intrinsic(level), False
            )
            for leg, n in legs
        )

    def max_loss(self, units: Mapping[str, int], cash_flow: float, market: Market) -> float:
        return self.of_legs(self._legs({c: n for c, n in units.items() if n}, market), cash_flow)

    def of_legs(self, legs: list[tuple[Leg, int]], cash_flow: float) -> float:
        """The same model on (leg, units) pairs and the cash moved so far (scoreboard A's one-lot unit, story S3)."""
        for kind in (OPTION_CALL, OPTION_PUT):
            if sum(leg.side * n for leg, n in legs if leg.kind == kind) < 0:
                raise RiskInputError(f"more {kind} units sold than bought: the maximum loss is not fixed")
        if not legs:
            return 0.0
        worst = max(
            (round(-sum(leg.side * n * leg.intrinsic(level) for leg, n in legs), 6), self._exit_charges(legs, level))
            for level in {leg.strike for leg, _ in legs}
        )
        exit_pads = self.pad * sum(n for _, n in legs)
        return max(worst[0] - cash_flow + exit_pads + worst[1], 0.0)


class PositionRisks:
    """Each open trade's and the proposal's buckets and maximum loss, and each session trade's new risk."""

    def __init__(self, buckets: BucketMap, held: HeldMaxLoss, costs: TradeCosts):
        self.buckets, self.held, self.costs = buckets, held, costs

    def of_open(self, trade: OpenTrade, market: Market) -> PositionRisk:
        buckets = self.buckets.buckets_of(trade.terms.structure, trade.units)
        return PositionRisk(trade.trade_id, buckets, self.held.max_loss(trade.units, trade.cash_flow, market))

    def of_proposal(self, proposal: Proposal, market: Market) -> PositionRisk:
        buckets = self.buckets.buckets_of(proposal.terms.structure, proposal.signed_units())
        return PositionRisk(proposal.trade_id, buckets, self.costs.max_loss(proposal, market))

    def of_session(self, trade: SessionTrade, market: Market) -> float:
        """The largest maximum loss the trade carried after any of the session's fill times (zero once flat)."""
        return max((self.held.max_loss(units, cash, market) for units, cash in trade.states), default=0.0)
