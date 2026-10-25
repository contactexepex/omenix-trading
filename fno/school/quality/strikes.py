"""The strike step of each expiry of a chain (story 3.5): an expiry's step is the most common gap between its listed
strikes (the smaller on a tie). Steps differ by expiry: on 22 Oct 2026 FINNIFTY's 27 Oct monthly lists 50-point
strikes and its 23 Nov monthly 100-point ones, so one step for the road would put a driver on an unlisted strike and
shrink the band of the wider expiry."""

from collections import Counter
from collections.abc import Iterable
from datetime import date

from ..contracts.snapshot import ContractKey


def strike_steps(keys: Iterable[ContractKey]) -> dict[date, float]:
    """Expiry -> step, for every expiry with two or more strikes; an expiry with fewer has no step and is left out."""
    strikes: dict[date, set[float]] = {}
    for key in keys:
        strikes.setdefault(key.expiry, set()).add(key.strike)
    steps = {}
    for expiry, listed in strikes.items():
        ordered = sorted(listed)
        gaps = Counter(round(high - low, 6) for low, high in zip(ordered, ordered[1:], strict=False))
        if gaps:
            steps[expiry] = min(gaps, key=lambda gap: (-gaps[gap], gap))
    return steps
