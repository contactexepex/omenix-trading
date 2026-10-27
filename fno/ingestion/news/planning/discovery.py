"""`discovery-vN.json` (NP3b): the owner's private description of WHERE to look, in the private config area with the
discipline of every versioned file (`news/versioned.py`). It holds the search service's address and parameters, the
broad queries, the template for a company's own query, and the hand-listed publisher feeds. Nothing in code names the
service, a query or a company. A refusal is one fixed code and never names a line."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from urllib.parse import parse_qs, urlparse, urlsplit

from fno.ingestion.news import codes
from fno.ingestion.news.feeds import FEED_ID
from fno.ingestion.news.versioned import ErrorCodes, VersionedFiles
from fno.ingestion.storage.raw_store import RawFileStore

DISCOVERY_FOLDER = "discovery"
FORMAT = 1
MAX_BROAD, MAX_PUBLISHER_FEEDS, MAX_PARAMS, MAX_TEXT = 300, 100, 10, 200
TOP_KEYS = frozenset({"format", "search", "broad", "targeted_template", "publisher_feeds"})
SEARCH_KEYS = frozenset({"url", "query_param", "params"})
NAME_SLOT = "{name}"


class DiscoveryError(Exception):
    """`str(error)` is one of the fixed codes."""


@dataclass(frozen=True)
class DiscoveryPlan:
    version: int
    search_url: str = field(repr=False)
    query_param: str
    params: tuple[tuple[str, str], ...]
    broad: tuple[str, ...]
    targeted_template: str
    publisher_feeds: tuple[tuple[str, str], ...] = field(repr=False)  # (feed id, url)


def _invalid() -> DiscoveryError:
    return DiscoveryError(codes.DISCOVERY_INVALID)


def _https(url: object) -> str:
    if not isinstance(url, str) or len(url) > 500 or not url.startswith("https://"):
        raise _invalid()
    if not urlparse(url).hostname:
        raise _invalid()
    return url


def _texts(value: object, limit: int) -> tuple[str, ...]:
    if not isinstance(value, list) or len(value) > limit:
        raise _invalid()
    if not all(isinstance(v, str) and v.strip() and len(v) <= MAX_TEXT for v in value):
        raise _invalid()
    return tuple(value)


def _search(value: object) -> tuple[str, str, tuple[tuple[str, str], ...]]:
    if not isinstance(value, dict) or set(value) != SEARCH_KEYS:
        raise _invalid()
    params = value["params"]
    if not isinstance(params, dict) or len(params) > MAX_PARAMS:
        raise _invalid()
    if not all(
        isinstance(k, str) and isinstance(v, str) and k and len(k) + len(v) <= MAX_TEXT for k, v in params.items()
    ):
        raise _invalid()
    name = value["query_param"]
    if not isinstance(name, str) or not name or name in params:
        raise _invalid()
    url = _https(value["url"])
    if name in parse_qs(urlsplit(url).query):  # the query would be there twice
        raise _invalid()
    return url, name, tuple(sorted(params.items()))


def _publisher_feeds(value: object) -> tuple[tuple[str, str], ...]:
    if not isinstance(value, list) or len(value) > MAX_PUBLISHER_FEEDS:
        raise _invalid()
    feeds = []
    for item in value:
        if not isinstance(item, dict) or set(item) != {"id", "url"}:
            raise _invalid()
        feed_id = item["id"]
        if not isinstance(feed_id, str) or not feed_id.startswith("feed-") or not FEED_ID.match(feed_id):
            raise _invalid()
        feeds.append((feed_id, _https(item["url"])))
    if len({i for i, _ in feeds}) != len(feeds):
        raise _invalid()
    return tuple(feeds)


def parse_discovery(data: bytes, version: int) -> DiscoveryPlan:
    try:
        document = json.loads(data)
    except (ValueError, UnicodeDecodeError):
        raise _invalid() from None
    if not isinstance(document, dict) or set(document) != TOP_KEYS or document["format"] != FORMAT:
        raise _invalid()
    template = document["targeted_template"]
    if not isinstance(template, str) or template.count(NAME_SLOT) != 1 or len(template) > MAX_TEXT:
        raise _invalid()
    if template.replace(NAME_SLOT, "").count("{") or template.replace(NAME_SLOT, "").count("}"):
        raise _invalid()
    url, query_param, params = _search(document["search"])
    broad = _texts(document["broad"], MAX_BROAD)
    return DiscoveryPlan(
        version, url, query_param, params, broad, template, _publisher_feeds(document["publisher_feeds"])
    )


class PrivateDiscoveryFile:
    def __init__(self, store: RawFileStore, lowest_version: int = 0, used: Mapping[int, str] | None = None):
        """`store`: the private config area (read only)."""
        self.files = VersionedFiles(
            store, DISCOVERY_FOLDER, "discovery",
            ErrorCodes(codes.DISCOVERY_MISSING, codes.DISCOVERY_ROLLED_BACK, codes.DISCOVERY_DAMAGED), DiscoveryError,
        )  # fmt: skip
        self.lowest_version, self.used = lowest_version, used

    def plan(self) -> DiscoveryPlan:
        picked = self.files.latest(self.lowest_version, self.used)
        return parse_discovery(picked.data, picked.version)
