"""Where an article came from, as FACTS (NP2a): the outlet's host, the article's own URL when the feed gave one,
and how sure we are. Nothing here comes from a rule file: the tier, the wire and the promotional flag are computed when
the article is READ (NP5/NP6), so editing the allowlist or the watchlist never changes a recorded article's bytes.

- a publisher item with an https link: the link is the source URL, its host the source domain (`publisher`);
- a publisher item with no link, or one that is not https: nothing (`none`);
- a Google News item: the link is a redirect wrapper and is NOT the source. The only host we have is the `url` of
  Google's own <source> element, taken only when it is https and a plain host name; the URL stays empty until the link
  is resolved (`undecoded`; NP2b)."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit

from fno.ingestion.news.article.keys import PUBLISHER
from fno.ingestion.news.sources.rules import plain_host

URL_PUBLISHER, URL_UNDECODED, URL_NONE = "publisher", "undecoded", "none"
URL_STATUSES = (URL_PUBLISHER, URL_UNDECODED, URL_NONE)
HTTPS = "https"


@dataclass(frozen=True)
class SourceFacts:
    domain: str = ""
    url: str = ""
    status: str = ""


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


def source_facts(kind: str, link_canonical: str, source_url: str) -> SourceFacts:
    """`link_canonical`: the canonical form of a publisher item's link ("" for none); `source_url`: the <source> url."""
    if kind == PUBLISHER:
        host = https_host(link_canonical) if link_canonical else ""
        return SourceFacts(host, link_canonical, URL_PUBLISHER) if host else SourceFacts("", "", URL_NONE)
    return SourceFacts(https_host(source_url), "", URL_UNDECODED)
