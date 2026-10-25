"""Fills, charges, pads and the modelled maximum loss of one position (story B2, protocol section 4).

Fills: bought legs at price + pad, sold legs at price - pad, at entry and at exit. Charges per leg and per side through
`fno.costs.order_charges` with the `charges` block of `config.yaml`, on the filled price, at least one tick (Rs 0.05:
no order is filled lower, so every order pays brokerage). The modelled maximum loss is the largest terminal payoff
loss (width minus credit for a short structure, the debit for a long one) plus entry charges, all pads (every leg,
entry and exit) and the exit charges at the worst-case exit prices: each leg's terminal value at the index level where
the loss is largest (a strike: a covered position's payoff is flat or rising beyond its outer strikes); where
several levels give that loss, the one with the larger exit charges. Uncovered legs (a sold option without a bought
one of its type) are refused rather than priced (story STR1). It bounds the terminal payoff only: an exit at closes
that break no-arbitrage bounds can lose more (tests/research_engine/test_cycles_real.py, July 2024).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from ..constants import SIDE_BUY, SIDE_SELL
from ..costs import order_charges
from .structures import Leg, require_covered, terminal_value

OPTION_TICK = 0.05  # NSE's smallest option price: every order, a worst-case exit at zero value included, pays charges
PAD = 1.0  # rupees per unit, worse on every leg at entry and at exit
LOSS_CAP = 10_000.0  # the owner's cap on one trade's modelled maximum loss, rupees
LOSS_DECIMALS = 6  # equal terminal losses at two levels compare equal despite float sums
WIDTHS = (300.0, 250.0, 200.0, 150.0, 100.0)  # wing widths tried, largest first


@dataclass(frozen=True)
class CycleTerms:
    lot: int  # units per lot (NIFTY: config.yaml lot_sizes); one lot is traded
    charges: Mapping[str, float]  # config.yaml `charges`
    pad: float = PAD
    cap: float = LOSS_CAP
    widths: tuple[float, ...] = WIDTHS


class PositionCosts:
    def __init__(self, terms: CycleTerms):
        self.terms = terms

    def fill(self, leg: Leg, price: float, opening: bool) -> float:
        buying = leg.bought == opening
        return price + self.terms.pad if buying else price - self.terms.pad

    def leg_charges(self, leg: Leg, price: float, opening: bool) -> float:
        buying = leg.bought == opening
        filled = max(self.fill(leg, price, opening), OPTION_TICK)
        return order_charges(filled, self.terms.lot, SIDE_BUY if buying else SIDE_SELL, dict(self.terms.charges))

    def charges(self, legs: Sequence[Leg], prices: Sequence[float], opening: bool) -> float:
        return sum(self.leg_charges(leg, price, opening) for leg, price in zip(legs, prices, strict=True))

    def pads(self, legs: Sequence[Leg]) -> float:
        """Every leg's pad at entry and at exit, in rupees."""
        return 2 * len(legs) * self.terms.pad * self.terms.lot

    def gross(self, legs: Sequence[Leg], entry: Sequence[float], exit_: Sequence[float]) -> float:
        """P&L at the raw (unpadded) prices, in rupees."""
        return sum(leg.side * (x - e) for leg, e, x in zip(legs, entry, exit_, strict=True)) * self.terms.lot

    def max_loss(self, legs: Sequence[Leg], entry: Sequence[float]) -> float:
        """Modelled maximum loss in rupees: terminal payoff loss, entry charges, all pads, worst-case exit charges."""
        require_covered(legs)
        payoff_loss, exit_charges = max(
            (round(loss, LOSS_DECIMALS), self.charges(legs, [leg.intrinsic(level) for leg in legs], False))
            for level, loss in _terminal_losses(legs, entry).items()
        )
        return payoff_loss * self.terms.lot + self.charges(legs, entry, True) + self.pads(legs) + exit_charges


def _terminal_losses(legs: Sequence[Leg], entry: Sequence[float]) -> dict[float, float]:
    """Index level at expiry (each strike) -> the position's loss per unit there, entry premium included."""
    credit = -sum(leg.side * price for leg, price in zip(legs, entry, strict=True))
    return {leg.strike: -(terminal_value(legs, leg.strike) + credit) for leg in legs}
