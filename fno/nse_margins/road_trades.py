"""Story MS-P1m: a market school trade as C2 sees it. `RoadTradeTerms` is C2's `TradeTerms` plus the index, the expiry,
the legs and the units per lot, checked against its structure's shape. C2's `MarginRoom` prices the margin from the
terms but counts units and cash from the `Proposal` or `OpenTrade`, so both are built here from the same terms: a lot
or a leg can never differ between the margin and the trade (self-review, 22 Oct 2026: a lot of 1 inside a 65-unit
proposal passed with Rs 840 needed instead of Rs 54,600)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from ..constants import (
    NIFTY_SYMBOL,
    OPTION_CALL,
    OPTION_PUT,
    RECORDED_INDEX_OPTIONS,
    STRUCTURE_CALL_CREDIT_SPREAD,
    STRUCTURE_CALL_DEBIT_SPREAD,
    STRUCTURE_LONG_IRON_FLY,
    STRUCTURE_PUT_CREDIT_SPREAD,
    STRUCTURE_PUT_DEBIT_SPREAD,
    STRUCTURE_SHORT_CONDOR,
    STRUCTURE_SHORT_IRON_FLY,
)
from ..research_engine.structures import Leg
from ..risk.inputs import OpenTrade, Proposal, ProposedLeg, RiskInputError, TradeTerms

ROAD_UNDERLYINGS = (NIFTY_SYMBOL, *RECORDED_INDEX_OPTIONS)
# One-side codes: the option type and whether the sold leg is the higher strike (a bull put spread sells the higher put)
ONE_SIDE_SHAPES = {
    STRUCTURE_PUT_CREDIT_SPREAD: (OPTION_PUT, True), STRUCTURE_CALL_CREDIT_SPREAD: (OPTION_CALL, False),
    STRUCTURE_PUT_DEBIT_SPREAD: (OPTION_PUT, False), STRUCTURE_CALL_DEBIT_SPREAD: (OPTION_CALL, True),
}  # fmt: skip
BODY_SOLD = {STRUCTURE_SHORT_IRON_FLY: True, STRUCTURE_SHORT_CONDOR: True, STRUCTURE_LONG_IRON_FLY: False}
NOT_ITS_SHAPE = "school trade: {structure} {width:g} legs {legs} are not its shape ({why})"
ContractOf = Callable[[str, date, Leg], str]  # (index, expiry, leg) -> the contract id the market quotes


@dataclass(frozen=True)
class RoadTradeTerms(TradeTerms):
    """A school trade: C2's terms plus the index, the expiry, the legs (one unit each) and the units per lot."""

    underlying: str
    expiry: date
    legs: tuple[Leg, ...]
    lot: int

    def __post_init__(self):
        super().__post_init__()
        if self.underlying not in ROAD_UNDERLYINGS or self.lot <= 0 or not self.legs:
            raise RiskInputError(f"school trade: {self.underlying} lot {self.lot} with {len(self.legs)} legs")
        why = _shape_problem(self.structure, self.width, self.legs)
        if why:
            legs = " ".join(f"{leg.side:+d}x{leg.strike:g}{leg.kind}" for leg in self.legs)
            raise RiskInputError(NOT_ITS_SHAPE.format(structure=self.structure, width=self.width, legs=legs, why=why))

    @property
    def what(self) -> str:
        return f"{self.underlying} {self.structure} {self.width:g} {self.expiry}"


def road_proposal(trade_id: str, terms: RoadTradeTerms, contract_of: ContractOf) -> Proposal:
    """C2's proposal with the terms' own lot and legs."""
    legs = tuple(ProposedLeg(contract_of(terms.underlying, terms.expiry, leg), leg) for leg in terms.legs)
    return Proposal(trade_id, terms, terms.lot, legs)


def road_open_trade(trade_id: str, terms: RoadTradeTerms, contract_of: ContractOf, cash_flow: float) -> OpenTrade:
    """C2's open trade with the units the terms imply: side x lot x lots per leg."""
    units = {contract_of(terms.underlying, terms.expiry, leg): leg.side * terms.lot * terms.lots for leg in terms.legs}
    return OpenTrade(trade_id, terms, units, cash_flow)


def _shape_problem(structure: str, width: float, legs: tuple[Leg, ...]) -> str | None:
    if any(abs(leg.side) != 1 for leg in legs):
        return "one unit per leg"
    if structure in ONE_SIDE_SHAPES:
        return _one_side_problem(structure, width, legs)
    if structure in BODY_SOLD:
        return _four_leg_problem(BODY_SOLD[structure], structure == STRUCTURE_SHORT_CONDOR, width, legs)
    return f"{structure} is not a school structure"


def _one_side_problem(structure: str, width: float, legs: tuple[Leg, ...]) -> str | None:
    kind, sold_higher = ONE_SIDE_SHAPES[structure]
    if len(legs) != 2 or {leg.kind for leg in legs} != {kind} or sorted(leg.side for leg in legs) != [-1, 1]:
        return f"one bought and one sold {kind}"
    low, high = sorted(legs, key=lambda leg: leg.strike)
    if high.strike - low.strike != width:
        return f"{high.strike - low.strike:g} wide"
    return None if (high.side < 0) == sold_higher else "the wrong leg is sold"


def _four_leg_problem(body_sold: bool, condor: bool, width: float, legs: tuple[Leg, ...]) -> str | None:
    """A body (one call and one put on the body's side) and two wings `width` further out, one of each type."""
    body_side = -1 if body_sold else 1
    by = {(leg.kind, leg.side): leg.strike for leg in legs}
    wanted = [(kind, side) for kind in (OPTION_CALL, OPTION_PUT) for side in (body_side, -body_side)]
    if len(legs) != 4 or sorted(by) != sorted(wanted):
        return "one call and one put in the body, one of each in the wings"
    call, put = by[(OPTION_CALL, body_side)], by[(OPTION_PUT, body_side)]
    out = (by[(OPTION_CALL, -body_side)] - call, put - by[(OPTION_PUT, -body_side)])
    if all(distance < 0 for distance in out):
        return "the wrong legs are sold (the wings sit inside the body)"
    if out != (width, width):
        return f"wings not {width:g} out"
    if condor and call <= put:
        return "a condor's sold call is above its sold put"
    return None if condor or call == put else "a fly's body is one strike"
