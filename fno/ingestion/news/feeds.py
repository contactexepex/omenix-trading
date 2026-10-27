"""The private feed list (P2, R1): feed ids and their URLs live in Drive, never in this repository. The list is stored
as write-once versions `feeds/feeds-v<N>.json`; the newest version by number is used, and a version older than one
already used is refused (no rolling back by deleting). The owner adds a version instead of editing one in place, so
the verified store never meets a changed file. Errors carry a fixed code only: the file's text is never put in a
message."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from urllib.parse import urlparse

from fno.ingestion.news import codes
from fno.ingestion.storage.raw_store import RawFileStore

FEEDS_FOLDER = "feeds"
VERSION_NAME = re.compile(r"^feeds-v(\d+)\.json$")
FEED_ID = re.compile(r"^feed-\d{2,3}$")
MAX_FEEDS = 50


class FeedListError(Exception):
    """The feed list cannot be used; `str(error)` is one of the fixed codes."""


@dataclass(frozen=True)
class FeedEntry:
    feed_id: str
    url: str = field(repr=False)  # never printed, even by a traceback

    @property
    def host(self) -> str:
        return urlparse(self.url).hostname or ""


@dataclass(frozen=True)
class FeedList:
    version: int
    feeds: tuple[FeedEntry, ...]


def parse_feed_list(data: bytes, version: int) -> FeedList:
    try:
        entries = json.loads(data)["feeds"]
        feeds = tuple(FeedEntry(item["id"], item["url"]) for item in entries)
    except (UnicodeDecodeError, ValueError, KeyError, TypeError):
        raise FeedListError(codes.FEED_LIST_INVALID) from None
    ids = [feed.feed_id for feed in feeds]
    valid = (
        0 < len(feeds) <= MAX_FEEDS
        and len(set(ids)) == len(ids)
        and all(FEED_ID.match(i) for i in ids)
        and all(isinstance(f.url, str) and f.url.startswith("https://") and f.host for f in feeds)
    )
    if not valid:
        raise FeedListError(codes.FEED_LIST_INVALID)
    return FeedList(version, feeds)


class PrivateFeedLists:
    def __init__(self, store: RawFileStore):
        """`store`: the private config area of Drive (read only here)."""
        self.store = store

    def latest(self, lowest_version: int = 0) -> FeedList:
        """The newest version; `lowest_version`: the newest already used, below which the run stops."""
        versions = {
            int(m.group(1)): name for name in self.store.checksums(FEEDS_FOLDER) if (m := VERSION_NAME.match(name))
        }
        if not versions:
            raise FeedListError(codes.FEED_LIST_MISSING)
        newest = max(versions)
        if newest < lowest_version:
            raise FeedListError(codes.FEED_LIST_ROLLED_BACK)
        data = self.store.get(f"{FEEDS_FOLDER}/{versions[newest]}")
        if data is None:
            raise FeedListError(codes.FEED_LIST_MISSING)
        return parse_feed_list(data, newest)
