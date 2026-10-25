"""Each issued row against its outcome (story "Outcome and scores"): the contract's mid at d+'s 3 pm from G13's record
of d+ (A4's canonical chain, the same source as d), only from a valid two-sided quote. Per row and method: the
quantile score in rupees, the relative score (rupees over max(d's mid, Rs 2)), inside 50% and inside 90%."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from ..price_distribution.scoring import quantile_score
from .constants import (
    DAYS_BUCKETS,
    DELTA_BUCKETS,
    LEVELS,
    METHODS,
    NO_NEXT_CHAIN,
    NO_NEXT_QUOTE,
    OTHER_SOURCE,
    RELATIVE_FLOOR,
)


@dataclass(frozen=True)
class Scored:
    """One row's scores per method: (rupee QS, relative QS, inside 50%, inside 90%)."""

    delta_bucket: int | None
    days_bucket: int | None
    by_method: dict[str, tuple[float, float, int, int]]


def delta_bucket(abs_delta: float) -> int | None:
    """|delta| buckets: the low end included, the high end not (the last has none)."""
    return next((i for i, (lo, hi) in enumerate(DELTA_BUCKETS) if abs_delta >= lo and (hi is None or abs_delta < hi)),
                None)  # fmt: skip


def days_bucket(days: int) -> int | None:
    """Days-to-expiry buckets: both ends included."""
    return next((i for i, (lo, hi) in enumerate(DAYS_BUCKETS) if days >= lo and (hi is None or days <= hi)), None)


def outcome_mids(next_record: dict | None) -> dict[tuple[str, float, str], float]:
    """(expiry, strike, side) -> the 3 pm mid at d+, two-sided quotes only."""
    if next_record is None:
        return {}
    found = {}
    for e in (next_record.get("valuation") or {}).get("expiries", []):
        for c in e.get("contracts", []):
            if c.get("bid") is not None and c.get("ask") is not None and c.get("price") is not None:
                found[(e["expiry"], c["strike"], c["kind"])] = c["price"]
    return found


def method_scores(quantiles, outcome: float, mid: float) -> tuple[float, float, int, int]:
    qs = quantile_score(LEVELS, outcome, quantiles)
    return (qs, qs / max(mid, RELATIVE_FLOOR), int(quantiles[1] <= outcome <= quantiles[3]),
            int(quantiles[0] <= outcome <= quantiles[4]))  # fmt: skip


def score_record(record: dict, next_record: dict | None) -> tuple[list[Scored], Counter]:
    """The scored rows of one issued day and the unscored ones counted by reason."""
    unscored = Counter()
    if next_record is None:
        unscored[NO_NEXT_CHAIN] = len(record["rows"])
        return [], unscored
    if next_record.get("source") != record.get("source"):
        unscored[OTHER_SOURCE] = len(record["rows"])
        return [], unscored
    mids, scored = outcome_mids(next_record), []
    for row in record["rows"]:
        outcome = mids.get((row["expiry"], row["strike"], row["side"]))
        if outcome is None:
            unscored[NO_NEXT_QUOTE] += 1
            continue
        delta = None if row["delta"] is None else delta_bucket(abs(row["delta"]))
        scored.append(Scored(delta, days_bucket(row["days"]),
                             {m: method_scores(row[m], outcome, row["mid"]) for m in METHODS}))  # fmt: skip
    return scored, unscored
