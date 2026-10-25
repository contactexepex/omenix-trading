"""One- and two-leg structures (story STR1): a bought call or put, and the four vertical spreads. Each is anchored at
the ATM strike (the listed strike nearest spot, the lower one on a tie), so SF is CCS plus PCS and BF is CDS plus PDS at
the same width. A strike rule away from ATM is a new code, as SC is SF's 2% variant.

`width` is points out of the money: for a bought option, how far its strike is from ATM (0 is ATM); for a spread, the
distance from the ATM leg to the other leg. Every sold leg is covered by a bought leg of the same type (`Structure.legs`
refuses anything else)."""

from __future__ import annotations

from ..constants import OPTION_CALL
from .structures import BOUGHT, Leg, Structure, atm_strike


def out_of_the_money(kind: str) -> int:
    """+1 when a higher strike is further out of the money (calls), -1 when a lower one is (puts)."""
    return 1 if kind == OPTION_CALL else -1


class BoughtOption(Structure):
    """LC and LP: buy one option `width` points out of the money from ATM."""

    def __init__(self, code: str, kind: str):
        self.code, self.kind = code, kind

    def build(self, strikes: set[float], spot: float, width: float) -> list[Leg]:
        if width < 0:
            raise ValueError(f"{self.code}: width {width:g} would be in the money; it must be 0 or more")
        strike = atm_strike(strikes, spot) + out_of_the_money(self.kind) * width
        return [Leg(strike, self.kind, BOUGHT)]


class VerticalSpread(Structure):
    """Two options of one type: the ATM leg on `atm_side` and the leg `width` points further out of the money on the
    other side. Bought ATM is a debit spread; sold ATM is a credit spread."""

    def __init__(self, code: str, kind: str, atm_side: int):
        self.code, self.kind, self.atm_side = code, kind, atm_side

    def build(self, strikes: set[float], spot: float, width: float) -> list[Leg]:
        if width <= 0:
            raise ValueError(f"{self.code}: width {width:g} must be above 0 (two legs on one strike cancel)")
        atm = atm_strike(strikes, spot)
        far = atm + out_of_the_money(self.kind) * width
        return [Leg(atm, self.kind, self.atm_side), Leg(far, self.kind, -self.atm_side)]
