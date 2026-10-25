"""The round-trip cost per trade (FACTORY_RULES section 2, input 3): a stated measured cost with its source (judge 259
note 1), or C1's charges for every leg in and out (or cash settlement) at config.yaml's rates plus each leg's measured
half-spread pad."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ..constants import SIDE_BUY, SIDE_SELL
from ..costs import order_charges, settlement_charges_breakdown


class RoundTripCost(Protocol):
    source: str

    def rupees(self) -> float: ...


@dataclass(frozen=True)
class StatedCost:
    measured: float
    source: str

    def rupees(self) -> float:
        return self.measured


@dataclass(frozen=True)
class Leg:
    side: str  # the opening side
    units: int
    entry: float  # premium per unit
    exit: float | None  # premium per unit when closed by an order
    settlement: float | None  # intrinsic value per unit when held to cash settlement
    pad: float  # measured half-spread per unit, paid on every order
    pad_source: str

    def rupees(self, charges: dict) -> float:
        closing = SIDE_SELL if self.side == SIDE_BUY else SIDE_BUY
        opening = order_charges(self.entry, self.units, self.side, charges) + self.pad * self.units
        if self.exit is not None:
            return opening + order_charges(self.exit, self.units, closing, charges) + self.pad * self.units
        return opening + sum(settlement_charges_breakdown(self.settlement, self.units, closing, charges).values())


@dataclass(frozen=True)
class LegsCost:
    legs: tuple[Leg, ...]
    charges: dict
    source: str = "C1 charges (config.yaml) plus measured pads"

    def rupees(self) -> float:
        return sum(leg.rupees(self.charges) for leg in self.legs)
