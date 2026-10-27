"""Where the resolver may send a request (NP2b). The allowed domain is NOT a constant in this repository: it is the
registrable domain of the host of each WRAPPER-kind feed in the owner's private feed list, read at run time (P2's
privacy test forbids any news-service host name in `fno/`). So the resolver can only ever call the service the
owner's own feed already calls, and a link on any other host is refused before anything is requested."""

from __future__ import annotations

from collections.abc import Iterable
from urllib.parse import urlsplit

from fno.ingestion.news.article.keys import WRAPPER
from fno.ingestion.news.article.source_facts import clean_https_link
from fno.ingestion.news.feeds import FeedEntry
from fno.ingestion.news.sources.model import is_public_suffix
from fno.ingestion.news.sources.rules import plain_host


def registrable_domain(host: str) -> str:
    """The last two labels, or the last three when those two are a public suffix (`co.uk`); "" for a non-host."""
    name = plain_host(host)
    labels = name.split(".")
    if len(labels) < 2:
        return ""
    two = ".".join(labels[-2:])
    if not is_public_suffix(two):
        return two
    return ".".join(labels[-3:]) if len(labels) >= 3 else ""  # a bare public suffix names nobody


class EgressGuard:
    def __init__(self, allowed_domains: Iterable[str]):
        self.allowed = frozenset(d for d in allowed_domains if d)

    def allows_host(self, host: str | None) -> bool:
        name = plain_host(host)
        return bool(name) and any(name == d or name.endswith("." + d) for d in self.allowed)

    def allows_link(self, link: str) -> bool:
        """True for a CLEAN https link (no whitespace or control character, credentials or port; see
        `clean_https_link`) whose host is on an allowed domain and which is ASCII throughout (a zero-width or look-alike
        character is not a link the service issued). `urlsplit` alone would read past a line break inside the host."""
        clean = clean_https_link(link)
        return bool(clean) and clean.isascii() and self.allows_host(urlsplit(clean).hostname)

    def __bool__(self) -> bool:
        return bool(self.allowed)


def guard_from_feeds(feeds: Iterable[FeedEntry]) -> EgressGuard:
    """Allow exactly the registrable domains of the wrapper feeds (an empty guard allows nothing)."""
    return EgressGuard(registrable_domain(f.host) for f in feeds if f.kind == WRAPPER)
