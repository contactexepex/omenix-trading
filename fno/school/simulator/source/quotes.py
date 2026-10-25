"""One archived close as a practice quote (story MS-SIM-c, 7.1 item 3).

The bid and ask are the close less and plus the scenario half-spread, rounded outward to a tick (the bid down, the ask
up), the half floored at half a tick. A bid that would not be above zero leaves the leg unsellable. Sizes are
`None` with `sizes_measured=False`: history holds no displayed size and none is invented. Only the practice rules of
MS-P1d's seam let such a quote through the size checks; the live laws and fills refuse it."""

import math

from ...contracts.snapshot import SlotQuote
from ..constants import TICK

EPSILON = 1e-9


def point_quote(close: float) -> SlotQuote:
    """The close as a quote of no width, for the impossible-price rule, which judges prices not ranges."""
    return SlotQuote(close, close, None, None, close, True, sizes_measured=False)


def practice_quote(close: float, relative_half_spread: float) -> SlotQuote:
    half = max(close * relative_half_spread, TICK / 2)
    bid = math.floor((close - half) / TICK + EPSILON) * TICK
    ask = math.ceil((close + half) / TICK - EPSILON) * TICK
    bid = round(max(bid, 0.0), 2)
    return SlotQuote(bid or None, round(ask, 2), None, None, close, True, sizes_measured=False)


def no_quote(close: float | None = None) -> SlotQuote:
    """A leg that cannot be priced: invalid, so the pilot's own gates refuse any trade that needs it."""
    return SlotQuote(None, None, None, None, close, False, sizes_measured=False)
