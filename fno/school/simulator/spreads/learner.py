"""Learning the spread model from recorded captures (story MS-SIM-b). Only our own hash-checked captures are read, as
`SlotSnapshot`s from MS-P1b's `CaptureReader`; nothing here fetches a quote or invents one.

A session's value for a bucket is the median relative half-spread of that bucket's valid two-sided quotes that session,
so a session with 200 strikes weighs the same as one with 3. A session counts once per bucket even when two roads of
one underlying (a monthly and a weekly capture) were recorded that day."""

from collections import defaultdict
from collections.abc import Iterable
from datetime import date
from statistics import median

from ...contracts.roads import ROADS_BY_CODE
from ...contracts.snapshot import SlotQuote, SlotSnapshot
from ..constants import TICK
from .bucket import SpreadBucket, bucket_of
from .model import SpreadModel


def relative_half_spread(quote: SlotQuote) -> float | None:
    """Half the gap as a share of the mid, the half floored at half a tick; None unless the quote is valid, two-sided
    and uncrossed."""
    if not quote.two_sided or quote.ask < quote.bid or not quote.mid or quote.mid <= 0:
        return None
    return max((quote.ask - quote.bid) / 2, TICK / 2) / quote.mid


class SpreadLearner:
    def learn(self, snapshots: Iterable[SlotSnapshot]) -> SpreadModel:
        observed: dict[SpreadBucket, dict[date, list[float]]] = defaultdict(lambda: defaultdict(list))
        for snapshot in snapshots:
            underlying = ROADS_BY_CODE[snapshot.road].underlying
            for key, quote in snapshot.quotes.items():
                bucket = bucket_of(underlying, snapshot.spot, key.strike, snapshot.session, key.expiry)
                value = relative_half_spread(quote)
                if bucket is not None and value is not None:
                    observed[bucket][snapshot.session].append(value)
        return SpreadModel({b: {d: median(v) for d, v in days.items()} for b, days in observed.items()})
