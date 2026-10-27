"""When a URL can say two articles are one story (NP6a; NP6 plan B1). The resolver and the feed readers keep any clean
https link, so a home page, a section page or a consent page could be an article's URL, and one such URL would merge
every article of a window by identity. A URL is an identity only when it points at one page of one story: it has a
query (after tracking parameters are removed) or at least two path segments, or one segment that looks like an article
slug or id (it holds a hyphen or a digit; `/markets` holds neither). **The rule is a guess** (reasoning only);
`url_joins_refused` counts what it turns away and `url_joins_unlike_title` (the file) counts the joins it accepted
although the titles disagree.

The normal form: lower-case host and no fragment (already so in a kept link), no `utm_*` and no `fbclid` parameter;
nothing else is changed, because some sites identify a story by another query parameter."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING_PREFIXES = ("utm_",)
TRACKING_NAMES = ("fbclid",)


@dataclass(frozen=True)
class Identity:
    url: str = ""  # the normal form, or "" when the link is no identity
    refused: bool = False  # there was a link, but it cannot identify a story


def _tracking(name: str) -> bool:
    lowered = name.lower()
    return lowered in TRACKING_NAMES or lowered.startswith(TRACKING_PREFIXES)


def _specific(segments: list[str], query: str) -> bool:
    if query or len(segments) >= 2:
        return True
    return len(segments) == 1 and any(ch == "-" or ch.isdigit() for ch in segments[0])


def identity_of(url: str) -> Identity:
    if not url:
        return Identity()
    parts = urlsplit(url)
    kept = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if not _tracking(k)]
    query = urlencode(kept)
    segments = [segment for segment in parts.path.split("/") if segment]
    if not _specific(segments, query):
        return Identity(refused=True)
    return Identity(urlunsplit((parts.scheme, parts.netloc, parts.path, query, "")))
