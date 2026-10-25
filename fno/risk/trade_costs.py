"""A proposal's money at entry: its modelled maximum loss, its entry cash flow and the funds a broker takes at entry
(story C2).

The risk manager depends on the `TradeCosts` interface; `SimulatorTradeCosts` is the one implementation and reuses the
cycle simulator's cost model (story B2: pads, every charge from `fno.costs`, worst-case exit charges), so the risk
manager, the research and the cap agree to the rupee on what a trade can lose.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from ..research_engine.cycle_costs import PAD, CycleTerms, PositionCosts
from ..research_engine.structures import BOUGHT
from .inputs import Market, Proposal


class TradeCosts(Protocol):
    def max_loss(self, proposal: Proposal, market: Market) -> float:
        """The most the trade can lose in rupees, every charge and pad included."""

    def entry_cash_flow(self, proposal: Proposal, market: Market) -> float:
        """Cash the entry moves: premium received minus paid at the padded fill prices, minus entry charges."""

    def entry_funds(self, proposal: Proposal, market: Market) -> float:
        """Funds the entry takes from free cash at once: the bought legs' premium at the padded fill prices plus every
        entry charge. The sold premium is not credited at entry (Groww, judge 77 addendum 3)."""


class SimulatorTradeCosts:
    def __init__(self, charges: Mapping[str, float], pad: float = PAD):
        self.charges, self.pad = dict(charges), pad

    def _costs(self, proposal: Proposal) -> PositionCosts:
        """B2's model for the whole order: every leg is one order of lots x lot size units."""
        return PositionCosts(CycleTerms(lot=proposal.units, charges=self.charges, pad=self.pad))

    def max_loss(self, proposal: Proposal, market: Market) -> float:
        legs = [p.leg for p in proposal.legs]
        return self._costs(proposal).max_loss(legs, proposal.entry_prices(market))

    def _entry(self, proposal: Proposal, market: Market) -> tuple[list[tuple[int, float]], float]:
        """Each leg's opening side and padded fill price (never below zero), and the entry's charges."""
        costs, legs, prices = self._costs(proposal), [p.leg for p in proposal.legs], proposal.entry_prices(market)
        fills = [max(costs.fill(leg, price, opening=True), 0.0) for leg, price in zip(legs, prices, strict=True)]
        return [(leg.side, fill) for leg, fill in zip(legs, fills, strict=True)], costs.charges(legs, prices, True)

    def entry_cash_flow(self, proposal: Proposal, market: Market) -> float:
        fills, charges = self._entry(proposal, market)
        return -sum(side * fill for side, fill in fills) * proposal.units - charges

    def entry_funds(self, proposal: Proposal, market: Market) -> float:
        fills, charges = self._entry(proposal, market)
        return sum(fill for side, fill in fills if side == BOUGHT) * proposal.units + charges
