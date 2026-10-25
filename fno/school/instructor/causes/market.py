"""Cause 8's market-wide move (story MS-INS, part c): each of the four index underlyings' `z` between the path's first
and last recorded snapshots, from its own monthly road's snapshots and the ATM volatility of its nearest expiry still
alive after the window. NIFTY's weekly road shares NIFTY's move. A settled path's own move runs to the settlement
price; the market's stops at the last recorded snapshot, as no other index has a 15:30 settlement capture."""

from datetime import date

from ...constants import RoadCode
from ..attribution.points import MINUTES_PER_YEAR, forward_of
from ..ports import SnapshotArchive
from .terms import atm_volatility, move_z

MARKET_ROADS = (RoadCode.NIFTY_MONTHLY, RoadCode.BANKNIFTY_MONTHLY, RoadCode.FINNIFTY_MONTHLY,
                RoadCode.MIDCPNIFTY_MONTHLY)  # fmt: skip


def market_moves(archive: SnapshotArchive, first: date, last: date, rate: float) -> tuple[float, ...]:
    """The `z` of every underlying measurable from `first` to `last` (both recorded, a positive time apart)."""
    moves = []
    for road in MARKET_ROADS:
        start, end = archive.snapshot(road, first), archive.snapshot(road, last)
        expiry = None if start is None else next((e for e in start.expiries if e > last), None)
        if end is None or expiry is None:
            continue  # its volatility is read on an expiry alive over the whole window, never one about to expire
        sigma = atm_volatility(start, expiry, forward_of(start, expiry, rate), rate)
        held = (end.finished_at - start.finished_at).total_seconds() / 60 / MINUTES_PER_YEAR
        z = move_z(start.spot, end.spot, sigma, held)
        moves += [z] if z is not None else []
    return tuple(moves)
