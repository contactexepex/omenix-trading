"""Expiry settlement of a school position (stories 3.1 and 3.6, E7 generalised): every leg closes at its intrinsic
value against the index's final settlement price, with C1's settlement charges, at the expiry day's 15:30 close. No
price yet means `settlement_needed`, never a guess. A position spans one expiry (law 1 refuses any other)."""

from collections.abc import Mapping
from datetime import date, datetime

from ...accounting.ledgers import Order
from ...desk.settlement import SETTLEMENT_TIME
from ...models import IST
from ..constants import SIDE_BUY, SIDE_SELL, ExitState
from ..contracts.accounts import FilledLeg, FillResult, IndexSettlementSource, SettlementUnavailable
from ..contracts.decisions import LegSpec, OpenPosition
from ..contracts.roads import ROADS_BY_CODE
from .desk_view import desk_leg

CLOSING_SIDE = {SIDE_BUY: SIDE_SELL, SIDE_SELL: SIDE_BUY}


def settlement_fill(position: OpenPosition, expiry: date, settlements: IndexSettlementSource,
                    charges: Mapping[str, float]) -> FillResult:  # fmt: skip
    if {leg.key.expiry for leg in position.legs} != {expiry}:
        raise ValueError(f"{position.position_id} does not expire wholly on {expiry}")
    underlying = ROADS_BY_CODE[position.road].underlying
    try:
        final = settlements.price(underlying, expiry)
    except SettlementUnavailable:
        return FillResult(state=ExitState.SETTLEMENT_NEEDED)
    legs = tuple(_settled(underlying, leg, position.lot, final.price, charges) for leg in position.legs)
    return FillResult(legs, filled_at=datetime.combine(expiry, SETTLEMENT_TIME, IST), rests_on=final.file_sha256)


def settled_order(side: str, price: float, units: int) -> Order:
    """A settlement close as C1 charges it (STT on an exercised long's intrinsic value, no exchange charges)."""
    return Order(side, price, units, 0.0, settlement=True)


def _settled(underlying: str, leg: LegSpec, lot: int, price: float, charges: Mapping[str, float]) -> FilledLeg:
    side, units = CLOSING_SIDE[leg.side], leg.lots * lot
    intrinsic = desk_leg(underlying, leg).leg.intrinsic(price)
    paid = sum(settled_order(side, intrinsic, units).charges(dict(charges)).values())
    return FilledLeg(leg.key, side, units, intrinsic, paid)
