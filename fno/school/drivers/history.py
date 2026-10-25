"""What a driver may know of the road's past (story MS-P1e, story 3.2): its own recorded 15:00 spots of earlier
sessions, never today's snapshot and never a later day. Every window needs its full length, else the driver says
"not enough history"."""

import math
import statistics
from dataclasses import dataclass
from datetime import date

from ..contracts.decisions import SpotPoint

HALF_STRADDLE = math.sqrt(2 / math.pi)  # a straddle's mid is about this share of one sigma of the move to expiry


@dataclass(frozen=True)
class SpotWindow:
    spots: tuple[float, ...]  # oldest first, exactly the window's length

    @property
    def mean(self) -> float:
        return statistics.fmean(self.spots)

    @property
    def high(self) -> float:
        return max(self.spots)

    @property
    def low(self) -> float:
        return min(self.spots)

    def daily_volatility(self) -> float:
        """Standard deviation of the session-to-session log returns of the window's spots."""
        return statistics.stdev(math.log(b / a) for a, b in zip(self.spots, self.spots[1:], strict=False))

    def straddle_equivalent(self, spot: float, sessions: int) -> float:
        """The straddle mid this realised volatility implies to an expiry `sessions` sessions away, in index points."""
        return HALF_STRADDLE * spot * self.daily_volatility() * math.sqrt(sessions)


def spot_window(history: tuple[SpotPoint, ...], session: date, length: int) -> SpotWindow | None:
    """The last `length` recorded spots strictly before `session`, or None when there are fewer."""
    earlier = sorted({p.session: p for p in history if p.session < session}.values(), key=lambda p: p.session)
    return SpotWindow(tuple(p.spot for p in earlier[-length:])) if len(earlier) >= length else None
