"""The expected move (story 3.2): the mid of the ATM straddle of one expiry at the snapshot. Model-free, one rule for
every index; no VIX. The ATM strike is the listed strike nearest spot (the lower on a tie) with a two-sided call and
put."""

from dataclasses import dataclass
from datetime import date

from ..constants import OptionKind
from ..contracts.snapshot import ContractKey, SlotSnapshot


@dataclass(frozen=True)
class ExpectedMove:
    atm_strike: float
    straddle_mid: float  # rupees per unit: the expected move in index points


def expected_move(snapshot: SlotSnapshot, expiry: date, max_distance: float) -> ExpectedMove | None:
    strikes = sorted({k.strike for k, q in snapshot.quotes.items() if k.expiry == expiry and q.two_sided})
    both = [
        s for s in strikes if _mid(snapshot, expiry, s, OptionKind.CALL) and _mid(snapshot, expiry, s, OptionKind.PUT)
    ]
    if not both:
        return None
    atm = min(both, key=lambda s: (abs(s - snapshot.spot), s))
    if abs(atm - snapshot.spot) > max_distance:
        return None  # a straddle this far from the money is mostly intrinsic value, not an expected move
    return ExpectedMove(atm, _mid(snapshot, expiry, atm, OptionKind.CALL) + _mid(snapshot, expiry, atm, OptionKind.PUT))


def _mid(snapshot: SlotSnapshot, expiry: date, strike: float, kind: OptionKind) -> float | None:
    quote = snapshot.quote(ContractKey(expiry, strike, kind))
    return quote.mid if quote is not None else None
