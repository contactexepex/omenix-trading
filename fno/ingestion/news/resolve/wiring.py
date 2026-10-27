"""Composition root of the link resolver (NP2b): the only place that picks the concrete adapter. Swapping the library
for our own small adapter is one new class behind `LinkResolver` and one line here."""

from __future__ import annotations

from collections.abc import Iterable

from fno.ingestion.news.feeds import FeedEntry
from fno.ingestion.news.resolve.decoder_adapter import GoogleNewsDecoderResolver
from fno.ingestion.news.resolve.guard import guard_from_feeds
from fno.ingestion.news.resolve.model import LinkResolver


def build_link_resolver(feeds: Iterable[FeedEntry]) -> LinkResolver:
    """A resolver allowed to call only the domains of the wrapper feeds in `feeds` (the private feed list)."""
    return GoogleNewsDecoderResolver(guard_from_feeds(feeds))
