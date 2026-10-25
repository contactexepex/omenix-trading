"""Spread buckets (story MS-SIM-b, 7.2): the road's underlying x how far the strike is from the money x days to expiry.

The band edges are first values, frozen with the practice card (reasoning only): moneyness |strike - spot| / spot in
[0,1%), [1,2%), [2,4%), [4%, inf); days to expiry (calendar) 0-7, 8-21, 22-45, 46+."""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

MONEYNESS_EDGES = (0.01, 0.02, 0.04)
DTE_EDGES = (7, 21, 45)


class Moneyness(StrEnum):
    NEAR = "under 1%"
    MID = "1-2%"
    FAR = "2-4%"
    DEEP = "4% and more"


class DaysToExpiry(StrEnum):
    WEEK = "0-7 days"
    MONTH = "8-21 days"
    CYCLE = "22-45 days"
    LONG = "46+ days"


@dataclass(frozen=True, order=True)
class SpreadBucket:
    underlying: str
    moneyness: Moneyness
    dte: DaysToExpiry

    def __str__(self) -> str:
        return f"{self.underlying}, strike {self.moneyness} from the money, {self.dte} to expiry"


def _band(value: float, edges: tuple[float, ...], names: tuple) -> StrEnum:
    return names[sum(1 for edge in edges if value >= edge)]


def bucket_of(underlying: str, spot: float, strike: float, session: date, expiry: date) -> SpreadBucket | None:
    """The bucket of a contract that session, or None for an expired contract or a spot that is not a price."""
    days = (expiry - session).days
    if days < 0 or spot <= 0:
        return None
    moneyness = _band(abs(strike - spot) / spot, MONEYNESS_EDGES, tuple(Moneyness))
    # the edges are inclusive upper bounds of a day band (7 is "0-7"), so the day count is compared with edge + 1
    dte = _band(days, tuple(edge + 1 for edge in DTE_EDGES), tuple(DaysToExpiry))
    return SpreadBucket(underlying, moneyness, dte)
