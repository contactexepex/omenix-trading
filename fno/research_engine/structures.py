"""Option structures (story B2, protocol section 4; story STR1). `Structure` builds any number of legs and refuses a
naked short leg: every sold call is matched by a bought call and every sold put by a bought put, so each position's
loss is fixed at entry. Experiment 1's protected four-leg structures (`BodyAndWings`: SF, SC, BF) are here; the one-
and two-leg ones (STR1) are in `one_side.py`.

Strikes: the nearest listed strike to the target; on an equal-distance tie the ATM strike is the lower one (as in F1)
and a short out-of-the-money leg takes the strike farther from spot (more conservative). A leg W points away must be
listed exactly, otherwise that width is unavailable. A covered position's terminal payoff is flat or rising beyond its
outer strikes, so its worst payoff lies at a strike.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from ..constants import (
    OPTION_CALL,
    OPTION_PUT,
    STRUCTURE_LONG_IRON_FLY,
    STRUCTURE_SHORT_CONDOR,
    STRUCTURE_SHORT_IRON_FLY,
)

BOUGHT, SOLD = 1, -1
CONDOR_OFFSET = 0.02  # SC sells the call nearest spot x 1.02 and the put nearest spot x 0.98

Contract = tuple[float, str]  # (strike, "CE" or "PE")
Chain = frozenset[Contract]  # the contracts of one expiry listed on one day


@dataclass(frozen=True)
class Leg:
    strike: float
    kind: str  # "CE" or "PE"
    side: int  # BOUGHT (+1) or SOLD (-1) when the position is opened

    @property
    def contract(self) -> Contract:
        return self.strike, self.kind

    @property
    def bought(self) -> bool:
        return self.side == BOUGHT

    def intrinsic(self, underlying: float) -> float:
        gap = underlying - self.strike if self.kind == OPTION_CALL else self.strike - underlying
        return max(gap, 0.0)


def terminal_value(legs: Iterable[Leg], underlying: float) -> float:
    """What the position is worth per unit at expiry with the index at `underlying` (bought legs count plus)."""
    return sum(leg.side * leg.intrinsic(underlying) for leg in legs)


def position_value(legs: Iterable[Leg], prices: Iterable[float]) -> float:
    """What the position is worth per unit at these leg prices (bought legs count plus)."""
    return sum(leg.side * price for leg, price in zip(legs, prices, strict=True))


class NakedShortLeg(ValueError):
    """A sold option without a bought option of the same type: its loss is not fixed at entry, so it is never built."""


def require_covered(legs: Sequence[Leg]) -> None:
    """Refuse a naked short leg: per option type, the legs sold may not outnumber the legs bought."""
    for kind in (OPTION_CALL, OPTION_PUT):
        if sum(leg.side for leg in legs if leg.kind == kind) < 0:
            shown = [(leg.strike, leg.kind, leg.side) for leg in legs]
            raise NakedShortLeg(f"more {kind} legs sold than bought: {shown}")


def payoff_bounds(legs: Sequence[Leg]) -> tuple[float, float]:
    """The least and most the position can be worth at expiry, per unit, over every index level from 0 up. Between 0
    and the top strike the payoff is linear between strikes; above it, it rises without limit when more calls are
    bought than sold. A market value outside these bounds is an impossible price: no-arbitrage keeps a position
    between its worst and best payoff."""
    values = [terminal_value(legs, level) for level in (0.0, *(leg.strike for leg in legs))]
    upward = sum(leg.side for leg in legs if leg.kind == OPTION_CALL)
    return -math.inf if upward < 0 else min(values), math.inf if upward > 0 else max(values)


def nearest_strike(strikes: Iterable[float], target: float, tie_higher: bool) -> float:
    """The listed strike nearest `target`; an equal-distance tie goes to the higher strike if `tie_higher`."""
    return min(strikes, key=lambda k: (abs(k - target), -k if tie_higher else k))


def atm_strike(strikes: Iterable[float], spot: float) -> float:
    """The ATM strike: the listed strike nearest spot, the lower one on a tie."""
    return nearest_strike(strikes, spot, tie_higher=False)


class Structure(ABC):
    """A position built from the day's listed contracts, spot and a width in points. `legs` is the one way to get its
    legs: it refuses a naked short leg whatever `build` returns."""

    code: str

    def legs(self, chain: Chain, spot: float, width: float) -> list[Leg] | None:
        """The legs for this width, or None when a needed contract is not listed (the width is unavailable)."""
        strikes = {strike for strike, _ in chain}
        if not strikes:
            return None
        legs = self.build(strikes, spot, width)
        require_covered(legs)
        return legs if all(leg.contract in chain for leg in legs) else None

    @abstractmethod
    def build(self, strikes: set[float], spot: float, width: float) -> list[Leg]:
        """The legs on these listed strikes (any number); `legs` checks they are listed and covered."""


class BodyAndWings(Structure):
    """A body (a call and a put on `body_side`) with a wing `width` points further out on the other side."""

    body_side: int

    def build(self, strikes: set[float], spot: float, width: float) -> list[Leg]:
        call, put = self.body_strikes(strikes, spot)
        return [
            Leg(call, OPTION_CALL, self.body_side),
            Leg(put, OPTION_PUT, self.body_side),
            Leg(call + width, OPTION_CALL, -self.body_side),
            Leg(put - width, OPTION_PUT, -self.body_side),
        ]

    @abstractmethod
    def body_strikes(self, strikes: set[float], spot: float) -> tuple[float, float]:
        """The body's (call strike, put strike)."""


class IronFly(BodyAndWings, ABC):
    """Body at the ATM strike."""

    def body_strikes(self, strikes: set[float], spot: float) -> tuple[float, float]:
        atm = atm_strike(strikes, spot)
        return atm, atm


class ShortIronFly(IronFly):
    """SF: sell the ATM call and put, buy each W away."""

    code, body_side = STRUCTURE_SHORT_IRON_FLY, SOLD


class LongIronFly(IronFly):
    """BF: buy the ATM call and put, sell each W away."""

    code, body_side = STRUCTURE_LONG_IRON_FLY, BOUGHT


class ShortCondor(BodyAndWings):
    """SC: sell the call nearest spot x 1.02 and the put nearest spot x 0.98, buy each W further out."""

    code, body_side = STRUCTURE_SHORT_CONDOR, SOLD

    def __init__(self, offset: float = CONDOR_OFFSET):
        """`offset`: the shorts' distance from spot as a fraction (EDGE1's SC3 passes 0.03; every other caller 0.02)."""
        self.offset = offset

    def body_strikes(self, strikes: set[float], spot: float) -> tuple[float, float]:
        call = nearest_strike(strikes, spot * (1 + self.offset), tie_higher=True)
        put = nearest_strike(strikes, spot * (1 - self.offset), tie_higher=False)
        return call, put
