"""Calibration rows (story section 2): for every expiry of a record with a distribution and a settled outcome, every
strike inside the measured CDF once, with `p = P(S_T > K)` (the call's chance; the put's is 1 - p, the same test) and
`y = 1` when the settlement is above K (equal is not above). Tail strikes are never rows."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date

from ..constants import OPTION_CALL
from .chances import ExpiryChances, itm_chance, region
from .constants import BIN_EDGES, BODY, HORIZON_BUCKETS, SOURCE_ALL, SOURCE_PREFERENCE
from .settlement import Settled


@dataclass(frozen=True)
class Row:
    day: date
    expiry: date
    days: int
    source: str
    strike: float
    p: float
    y: int


def rows_for(expiries: Iterable[ExpiryChances], settled: Mapping[date, Settled]) -> list[Row]:
    found = []
    for e in expiries:
        outcome = settled.get(e.expiry)
        if e.distribution is None or outcome is None or not outcome.usable:
            continue
        for strike in sorted({k for k, _ in e.contracts if region(e.distribution, k) == BODY}):
            p = itm_chance(e.distribution, strike, OPTION_CALL)
            found.append(Row(e.day, e.expiry, e.days, e.source, strike, p, int(outcome.price > strike)))
    return found


def of_source(rows: Iterable[Row], source: str) -> list[Row]:
    """One source's rows; `all`: per day and expiry the rows of the preferred source only (never both)."""
    rows = list(rows)
    if source != SOURCE_ALL:
        return [r for r in rows if r.source == source]
    best = {}
    for r in rows:
        rank = SOURCE_PREFERENCE.index(r.source)
        best[(r.day, r.expiry)] = min(best.get((r.day, r.expiry), rank), rank)
    return [r for r in rows if SOURCE_PREFERENCE.index(r.source) == best[(r.day, r.expiry)]]


def bucket_of(days: int) -> int:
    for i, (low, high) in enumerate(HORIZON_BUCKETS):
        if days >= low and (high is None or days <= high):
            return i
    raise ValueError(f"days to expiry {days} is in no bucket")


def bin_of(p: float) -> int:
    for i in range(len(BIN_EDGES) - 2):
        if p < BIN_EDGES[i + 1]:
            return i
    return len(BIN_EDGES) - 2


def bucket_name(index: int) -> str:
    low, high = HORIZON_BUCKETS[index]
    return f"{low}+ days" if high is None else f"{low}-{high} days"


def bin_name(index: int) -> str:
    return f"[{BIN_EDGES[index]:.2f}, {BIN_EDGES[index + 1]:.2f}{']' if index == len(BIN_EDGES) - 2 else ')'}"
