"""The resolution file (NP2c; NP0 section 2b): the publisher's real URL for one Google News article, in its own
write-once file `news/resolved/<key[:2]>/<key>.json`. The article file never changes and the article key never depends
on it (a re-polled item is rebuilt as unresolved, so a URL inside the article would make every re-poll a false
revision). Facts only: the URL, its host, the outlet the feed claimed, whether the two agree, and which resolver
found it. No time is written, so the same answer twice is the same bytes. A reader that sees no file has an
unresolved article, never an error."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from fno.ingestion.news.article.article_file import Article
from fno.ingestion.news.resolve.guard import registrable_domain
from fno.ingestion.news.sources.rules import plain_host

FORMAT = 1
RESOLVED_FOLDER = "news/resolved"
RESOLVER = "googlenewsdecoder 0.2.1"  # the library the adapter drives (hash-locked in requirements.lock)
KEYS = frozenset({"format", "key", "url", "host", "claimed_domain", "host_agrees", "resolver"})


def resolution_path(key: str) -> str:
    return f"{RESOLVED_FOLDER}/{key[:2]}/{key}.json"


def key_of_path(path: str) -> str:
    """The article key a resolution path belongs to: it is also the manifest id of the file."""
    return path.rsplit("/", 1)[-1].removesuffix(".json")


@dataclass(frozen=True)
class Resolution:
    key: str
    url: str
    host: str
    claimed_domain: str  # what the feed said ("" when it said nothing)
    host_agrees: bool  # the URL's site is the claimed outlet's site (same registrable domain)
    resolver: str = RESOLVER

    def to_bytes(self) -> bytes:
        document = {"format": FORMAT, **asdict(self)}
        return json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def build_resolution(article: Article, url: str) -> Resolution | None:
    """None when the URL has no plain host (the adapter has already checked it; this is the file's own check)."""
    from urllib.parse import urlsplit

    host = plain_host(urlsplit(url).hostname)
    if not host:
        return None
    claimed = article.source_domain
    agrees = bool(claimed) and registrable_domain(host) == registrable_domain(claimed) != ""
    return Resolution(article.key, url, host, claimed, agrees)


def parse_resolution(data: bytes) -> Resolution:
    document = json.loads(data)
    if not isinstance(document, dict) or set(document) != KEYS or document["format"] != FORMAT:
        raise ValueError("not a resolution file")
    fields = {k: v for k, v in document.items() if k != "format"}
    if not all(isinstance(fields[k], str) for k in ("key", "url", "host", "claimed_domain", "resolver")):
        raise ValueError("not a resolution file")
    if not isinstance(fields["host_agrees"], bool):
        raise ValueError("not a resolution file")
    return Resolution(**fields)
