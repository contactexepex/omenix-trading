"""The school's structures (story MS-P1e), built on B2's `Structure`, which refuses a naked short leg. A strike is a
target snapped to the nearest listed strike, as B2 does: on a tie a short out-of-the-money leg takes the strike
farther from spot (more conservative), an ATM leg the lower one."""

from ...constants import OPTION_CALL, OPTION_PUT
from ...research_engine.one_side import out_of_the_money
from ...research_engine.structures import BOUGHT, SOLD, Leg, ShortCondor, Structure, atm_strike, nearest_strike

PCS, CCS, CDS, PDS, SC, BF = "PCS", "CCS", "CDS", "PDS", "SC", "BF"  # B2's and STR1's codes


class AnchoredVertical(Structure):
    """Two options of one type: the anchor leg on `anchor_side` at the target strike (ATM when there is none), the
    other `width` points further out of the money. Sold anchor is a credit spread, bought anchor a debit spread."""

    def __init__(self, code: str, kind: str, anchor_side: int, target: float | None = None):
        self.code, self.kind, self.anchor_side, self.target = code, kind, anchor_side, target

    def build(self, strikes: set[float], spot: float, width: float) -> list[Leg]:
        if width <= 0:
            raise ValueError(f"{self.code}: width {width:g} must be above 0")
        if self.target is None:
            anchor = atm_strike(strikes, spot)
        else:  # the sold side of a spread sits farther from spot on a tie
            anchor = nearest_strike(strikes, self.target, tie_higher=self.kind == OPTION_CALL)
        far = anchor + out_of_the_money(self.kind) * width
        return [Leg(anchor, self.kind, self.anchor_side), Leg(far, self.kind, -self.anchor_side)]


class TargetCondor(ShortCondor):
    """A short iron condor whose sold call and put sit at the listed strikes nearest two targets."""

    def __init__(self, call_target: float, put_target: float):
        super().__init__()
        self.call_target, self.put_target = call_target, put_target

    def body_strikes(self, strikes: set[float], spot: float) -> tuple[float, float]:
        return (nearest_strike(strikes, self.call_target, tie_higher=True),
                nearest_strike(strikes, self.put_target, tie_higher=False))  # fmt: skip


class ExpectedMoveCondor(TargetCondor):
    """The reference and the weekly and ladder drivers' condor: both shorts one expected move from spot."""

    def __init__(self, spot: float, move: float):
        super().__init__(spot + move, spot - move)


class TargetFly(Structure):
    """A fly (both body legs on one strike, wings `width` either side): bought body is a long iron fly (BF)."""

    code = BF

    def __init__(self, body_side: int, target: float):
        self.body_side, self.target = body_side, target

    def build(self, strikes: set[float], spot: float, width: float) -> list[Leg]:
        body = nearest_strike(strikes, self.target, tie_higher=False)
        return [
            Leg(body, OPTION_CALL, self.body_side),
            Leg(body, OPTION_PUT, self.body_side),
            Leg(body + width, OPTION_CALL, -self.body_side),
            Leg(body - width, OPTION_PUT, -self.body_side),
        ]


def credit_vertical(kind: str, target: float) -> AnchoredVertical:
    """CS1's spread: the sold leg at the target, bought wing beyond (bull put for a put, bear call for a call)."""
    return AnchoredVertical(PCS if kind == OPTION_PUT else CCS, kind, SOLD, target)


def debit_vertical(kind: str, target: float | None = None) -> AnchoredVertical:
    """DR1's spread: the bought leg at the target (ATM without one), sold leg beyond (bull call, bear put)."""
    return AnchoredVertical(CDS if kind == OPTION_CALL else PDS, kind, BOUGHT, target)
