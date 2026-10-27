"""The F&O names a title may mention (P2c): a fixed list in code, so a change is a reviewed decision. An entity may
only move the similarity bar (`bar_for`); it never merges two articles by itself, and a wrong entry changes which
stories merge, never whether an article is kept. The list is a guess (reasoning only) and is re-tuned with the
threshold.
"""

from __future__ import annotations

from fno.ingestion.news.cluster.similarity import ENTITY_STEP, THRESHOLD

ENTITIES = frozenset({
    "nifty", "banknifty", "finnifty", "midcpnifty", "sensex",
    "reliance", "tcs", "infosys", "hdfcbank", "icicibank", "sbin", "itc", "axisbank", "kotakbank",
    "maruti", "tatamotors", "bajfinance", "adanient", "wipro", "hcltech", "larsentoubro", "sunpharma",
})  # fmt: skip


def entities_in(form: str) -> frozenset[str]:
    return ENTITIES.intersection(form.split())


def bar_for(a: frozenset[str], b: frozenset[str]) -> float:
    """The score two titles must reach: lower when they name a common entity, higher when each names only others. It
    is never zero, so an entity alone merges nothing."""
    if a & b:
        return THRESHOLD - ENTITY_STEP
    if a and b:
        return THRESHOLD + ENTITY_STEP
    return THRESHOLD
