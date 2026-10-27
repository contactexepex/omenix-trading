"""The article key (P2, D2, D3): a SHA-256 hex digest, by kind of item, so one record exists per item and two distinct
articles never share a key.

- a publisher item: its canonical URL (or, with no link, its guid); - a Google News item (a redirect wrapper that is
not resolved): its own guid, else the full publication time to the second, the normalised title, the normalised
summary and the source name (so "Stocks to watch today" printed twice on one day gives two keys, a minute apart).
Different outlets' copies of one story get different keys on purpose: clustering joins them, never the key."""

from __future__ import annotations

import hashlib
from datetime import datetime

from fno.ingestion.news.article.canonical import canonical_url
from fno.ingestion.news.article.normalise import normalise
from fno.ingestion.news.article.raw_item import RawItem

PUBLISHER, WRAPPER = "publisher", "wrapper"
KINDS = (PUBLISHER, WRAPPER)
SEPARATOR = "\x1f"  # cannot occur in the normalised parts, so "ab"+"c" and "a"+"bc" differ


def _digest(*parts: str) -> str:
    return hashlib.sha256(SEPARATOR.join(parts).encode("utf-8")).hexdigest()


def item_key(kind: str, item: RawItem, published: datetime | None) -> str:
    if kind == WRAPPER:
        if item.guid.strip():
            return _digest("google-news", "guid", item.guid.strip())
        moment = published.isoformat(timespec="seconds") if published else ""
        return _digest(
            "google-news", "text", moment, normalise(item.title), normalise(item.summary), normalise(item.source)
        )
    if item.link.strip():
        return _digest("publisher", "url", canonical_url(item.link))
    return _digest("publisher", "guid", item.guid.strip())
