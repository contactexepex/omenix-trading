"""One leg priced against the execution snapshot (story E4, design 6): it fills at the ask (buy) or the bid (sell) of
a valid A4 quote, and only when the size shown there covers all its units; otherwise it does not fill, with the reason.
A price is never taken from the last trade, another snapshot or a stale mark, and a leg never fills in part.

The pad is zero: crossing the spread is the slippage (E6 compares the half-spread paid with research's Rs 1 pad).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from ..constants import SIDE_BUY, SIDE_SELL
from ..research_engine.structures import Leg
from .snapshot import ExecutionQuote, ExecutionSnapshot

FILL_PAD_RS = 0.0
# Public reason (desk_events.csv): never the size shown, a per-contract quote figure (owner 6 A, decision 42).
NOT_ENOUGH_SIZE = "not enough size at the touch for {units} units"


@dataclass(frozen=True)
class DeskLeg:
    """One leg of a position: the exchange symbol the account records, its expiry, and strike, type and opening side."""

    contract: str
    expiry: date
    leg: Leg

    @property
    def protective(self) -> bool:
        """A bought leg protects the position: bought first and sold last (design 8)."""
        return self.leg.bought

    def side(self, opening: bool) -> str:
        return SIDE_BUY if self.leg.bought == opening else SIDE_SELL


@dataclass(frozen=True)
class LegQuote:
    """A leg's price at the snapshot, or why it has none (`price` None)."""

    leg: DeskLeg
    side: str
    units: int
    price: float | None
    reason: str  # empty when it fills
    quote: ExecutionQuote | None

    @property
    def fills(self) -> bool:
        return self.price is not None


def price_leg(snapshot: ExecutionSnapshot, leg: DeskLeg, side: str, units: int) -> LegQuote:
    quote = snapshot.quote(leg.expiry, leg.leg.strike, leg.leg.kind)
    if quote is None:
        return LegQuote(leg, side, units, None, "no quote in the snapshot", None)
    if quote.a4_problem:
        return LegQuote(leg, side, units, None, f"quote not valid: {quote.a4_problem}", quote)
    price, size = quote.touch(side)
    if size < units:
        return LegQuote(leg, side, units, None, NOT_ENOUGH_SIZE.format(units=units), quote)
    return LegQuote(leg, side, units, price, "", quote)


def quotable(snapshot: ExecutionSnapshot, leg: DeskLeg, side: str, units: int) -> bool:
    return price_leg(snapshot, leg, side, units).fills
