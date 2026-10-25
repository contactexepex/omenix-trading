"""C4's shape rules (story C4, design 12.4; story STR1): whether a proposal's legs are the structure its code names,
read from the legs and, for STR1's codes, the ATM strike C4 re-derives from the committed snapshot
(`Evidence.atm_strike`). Independent of B2 (no import of `fno.research_engine`): each rule restates the strike relations
in its own words. SF, SC and BF are checked on their relations only, as before STR1 (their anchor is not re-derived).

A naked short leg fails every shape: a sold leg always comes with a bought leg of its type one width further out."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence

from .validity_money import ProposedLeg

CALL, PUT = "CE", "PE"
BOUGHT, SOLD = 1, -1


def _away(kind: str) -> int:
    """+1 when a higher strike is further out of the money (calls), -1 when a lower one is (puts)."""
    return 1 if kind == CALL else -1


class Shape(ABC):
    @abstractmethod
    def problem(self, legs: Sequence[ProposedLeg], width: float, atm: float | None) -> str:
        """Why the legs are not this shape at this width ("" when they are); `atm` is the snapshot's ATM strike."""


class BodyWithWings(Shape):
    """SF, SC, BF: a body call and put on `body_side`, wings one width further out on the other side; one body strike
    (the iron flies) or the call body above the put body (the condor)."""

    def __init__(self, body_side: int, one_body_strike: bool):
        self.body_side, self.one_body_strike = body_side, one_body_strike

    def problem(self, legs: Sequence[ProposedLeg], width: float, atm: float | None) -> str:
        if len(legs) != 4:
            return f"needs four legs, not {len(legs)}"
        by_role = {(leg.kind, leg.side): leg.strike for leg in legs}
        try:
            call, put = by_role[(CALL, self.body_side)], by_role[(PUT, self.body_side)]
            call_wing, put_wing = by_role[(CALL, -self.body_side)], by_role[(PUT, -self.body_side)]
        except KeyError:
            return "the legs are not a body call and put with a wing on each side"
        if call_wing - call != width or put - put_wing != width:
            return f"wings are not {width:g} points beyond the body"
        if (call == put) != self.one_body_strike or call < put:
            return "the body strikes do not fit the structure"
        return ""


class OneBoughtOption(Shape):
    """LC, LP: one bought option of `kind`, `width` points out of the money from the ATM strike."""

    def __init__(self, kind: str):
        self.kind = kind

    def problem(self, legs: Sequence[ProposedLeg], width: float, atm: float | None) -> str:
        if len(legs) != 1:
            return f"needs one leg, not {len(legs)}"
        leg = legs[0]
        if (leg.kind, leg.side) != (self.kind, BOUGHT):
            return f"the leg must be a bought {self.kind}, not {'bought' if leg.side == BOUGHT else 'sold'} {leg.kind}"
        if width < 0:
            return f"width {width:g} is below 0"
        return _anchor_problem(leg.strike, atm + _away(self.kind) * width if atm is not None else None)


class Vertical(Shape):
    """CDS, CCS, PDS, PCS: two options of `kind`, the inner (ATM) one on `inner_side`, the outer one `width` points
    further out of the money on the other side."""

    def __init__(self, kind: str, inner_side: int):
        self.kind, self.inner_side = kind, inner_side

    def problem(self, legs: Sequence[ProposedLeg], width: float, atm: float | None) -> str:
        if len(legs) != 2 or any(leg.kind != self.kind for leg in legs):
            return f"needs two {self.kind} legs, not {[leg.kind for leg in legs]}"
        by_side = {leg.side: leg.strike for leg in legs}
        if set(by_side) != {BOUGHT, SOLD}:
            return "needs one bought and one sold leg"
        inner, outer = by_side[self.inner_side], by_side[-self.inner_side]
        if width <= 0 or (outer - inner) * _away(self.kind) != width:
            return f"the {'sold' if self.inner_side == BOUGHT else 'bought'} leg is not {width:g} points further out"
        return _anchor_problem(inner, atm)


def _anchor_problem(strike: float, expected: float | None) -> str:
    if expected is None:
        return "no ATM strike to check the strike against (the snapshot has no spot or no usable quote)"
    return "" if strike == expected else f"strike {strike:g} is not {expected:g} (the ATM strike rule)"


def shape_problem(
    shapes: Mapping[str, Shape], structure: str, legs: Sequence[ProposedLeg], width: float, atm: float | None
) -> str:
    """Why the legs are not the named structure's ("" when they are); an unknown code always fails."""
    shape = shapes.get(structure)
    if shape is None:
        return f"{structure} is not a known structure"
    problem = shape.problem(legs, width, atm)
    return f"{structure}: {problem}" if problem else ""
