"""The canonical URL of a publisher item (P2, D3): only an explicit allow-list of tracking parameters is removed, plus
the fragment and a default port; the scheme and host are lower-cased; every other parameter is kept, in sorted
order. So two URLs that differ in a non-tracking parameter stay two articles, and a real distinct article is never
merged away by the key."""

from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING_PARAMETERS = frozenset({"fbclid", "gclid", "igshid", "mc_cid", "mc_eid"})
TRACKING_PREFIXES = ("utm_",)
DEFAULT_PORTS = {"http": 80, "https": 443}


class UnreadableLink(Exception):
    """A link the standard library cannot split (a bad port, a broken IPv6 host). Carries no part of the link."""


def _is_tracking(name: str) -> bool:
    lowered = name.lower()
    return lowered in TRACKING_PARAMETERS or lowered.startswith(TRACKING_PREFIXES)


def canonical_url(url: str) -> str:
    """The canonical form; UnreadableLink (with no text of the link) when the standard library cannot split it."""
    try:
        parts = urlsplit(url.strip())
        scheme, host, port = parts.scheme.lower(), (parts.hostname or "").lower(), parts.port
    except ValueError:
        raise UnreadableLink from None
    netloc = host if port is None or port == DEFAULT_PORTS.get(scheme) else f"{host}:{port}"
    query = sorted((k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if not _is_tracking(k))
    return urlunsplit((scheme, netloc, parts.path, urlencode(query), ""))
