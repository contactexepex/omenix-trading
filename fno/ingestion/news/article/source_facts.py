"""Where an article came from, as FACTS (NP2a; NP0 section 3): the outlet's host, and for a Google News item the
redirect link kept so it can be resolved later. Nothing here comes from a rule file: the tier, the wire and the
promotional flag are computed when the article is READ (NP5/NP6), so editing the allowlist or the watchlist never
changes a recorded article's bytes. The resolved URL is not here either: it goes to its own write-once file (NP2c),
never into the article or its key.

- a publisher item: its source domain is the host of its https link ("" when it has none or it is not https);
- a Google News item: the link is a redirect wrapper and is NOT the source. The only host we have is the `url` of
  Google's own <source> element, taken only when it is https and a plain host name. The wrapper link itself is kept (so
  the item can be resolved from the Record alone), but only when it is a plain https link. No host name of a news
  service is written here: P2's privacy test forbids it. The resolver (NP2b) accepts only Google hosts and refuses the
  rest, so a wrapper link that points elsewhere is never requested."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit

from fno.ingestion.news.article.keys import PUBLISHER
from fno.ingestion.news.sources.rules import plain_host

HTTPS = "https"


@dataclass(frozen=True)
class SourceFacts:
    domain: str = ""
    wrapper_link: str = ""


def https_host(url: str) -> str:
    """The plain host of an https URL with no credentials and no port; "" for anything else."""
    try:
        parts = urlsplit(url.strip())
        if parts.scheme.lower() != HTTPS or parts.username is not None or parts.password is not None:
            return ""
        if parts.port not in (None, 443):
            return ""
        return plain_host(parts.hostname)
    except ValueError:
        return ""


def source_facts(kind: str, link_canonical: str, link: str, source_url: str) -> SourceFacts:
    """`link_canonical`: the canonical form of a publisher item's link ("" for none); `link`: the item's link as given;
    `source_url`: the `url` of its <source> element."""
    if kind == PUBLISHER:
        return SourceFacts(https_host(link_canonical) if link_canonical else "")
    wrapper = link.strip() if https_host(link) else ""
    return SourceFacts(https_host(source_url), wrapper)
