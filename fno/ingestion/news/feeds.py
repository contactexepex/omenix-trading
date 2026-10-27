"""The private feed list (P2, R1): feed ids and their URLs live in Drive, never in this repository. The list is stored
as write-once versions `feeds/feeds-v<N>.json`; the newest version by number is used, and a version older than one
already used is refused (no rolling back by deleting). The owner adds a version instead of editing one in place, so
the verified store never meets a changed file. Errors carry a fixed code only: the file's text is never put in a
message."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from urllib.parse import urlparse

from fno.ingestion.news import codes
from fno.ingestion.news.article.keys import KINDS
from fno.ingestion.news.versioned import ErrorCodes, VersionedFiles
from fno.ingestion.storage.raw_store import RawFileStore

FEEDS_FOLDER = "feeds"
FEED_ID = re.compile(r"^feed-\d{2,3}$")
MAX_FEEDS = 50
MIN_SALT_LENGTH = 16  # a random salt makes the list's logged SHA-256 useless for confirming a guessed list


class FeedListError(Exception):
    """The feed list cannot be used; `str(error)` is one of the fixed codes."""


@dataclass(frozen=True)
class FeedEntry:
    feed_id: str
    url: str = field(repr=False)  # never printed, even by a traceback
    kind: str = (
        "publisher"  # "wrapper" for a feed whose links are redirect wrappers (Google News): set in the private file
    )

    @property
    def host(self) -> str:
        return urlparse(self.url).hostname or ""


@dataclass(frozen=True)
class FeedList:
    version: int
    feeds: tuple[FeedEntry, ...]
    sha256: str = ""  # of the file as read, logged with every poll
    damaged: tuple[int, ...] = ()  # newer versions skipped because they were edited after use


def parse_feed_list(data: bytes, version: int) -> FeedList:
    try:
        document = json.loads(data)
        salt, entries = document["salt"], document["feeds"]
        feeds = tuple(FeedEntry(item["id"], item["url"], item.get("kind", "publisher")) for item in entries)
    except (UnicodeDecodeError, ValueError, KeyError, TypeError):
        raise FeedListError(codes.FEED_LIST_INVALID) from None
    ids = [feed.feed_id for feed in feeds]
    try:
        hosts_ok = all(
            f.host and f.host.encode("idna") for f in feeds
        )  # a host urllib3 would fail on is refused up front
    except (ValueError, UnicodeError, TypeError, AttributeError):
        raise FeedListError(codes.FEED_LIST_INVALID) from None
    valid = (
        isinstance(salt, str)
        and len(salt) >= MIN_SALT_LENGTH
        and 0 < len(feeds) <= MAX_FEEDS
        and len(set(ids)) == len(ids)
        and all(FEED_ID.match(i) for i in ids)
        and hosts_ok
        and all(f.kind in KINDS for f in feeds)
        and all(isinstance(f.url, str) and f.url.startswith("https://") for f in feeds)
    )
    if not valid:
        raise FeedListError(codes.FEED_LIST_INVALID)
    return FeedList(version, feeds, hashlib.sha256(data).hexdigest())


class PrivateFeedLists:
    def __init__(self, store: RawFileStore):
        """`store`: the private config area of Drive (read only here)."""
        self.files = VersionedFiles(
            store, FEEDS_FOLDER, "feeds",
            ErrorCodes(codes.FEED_LIST_MISSING, codes.FEED_LIST_ROLLED_BACK, codes.FEED_LIST_DAMAGED), FeedListError,
        )  # fmt: skip

    def latest(self, lowest_version: int = 0, used: Mapping[int, str] | None = None) -> FeedList:
        """The newest usable version. `lowest_version`: the newest already used, below which the run stops. `used`: the
        SHA-256 each used version had when it was used; a version whose file now differs was edited in place, is skipped
        (never silently) and the next older good one is used instead."""
        picked = self.files.latest(lowest_version, used)
        found = parse_feed_list(picked.data, picked.version)
        return FeedList(found.version, found.feeds, found.sha256, picked.damaged)

    def kinds_ever_listed(self) -> dict[str, str]:
        """Feed id -> kind over every valid version, so a feed retired from the newest list still has its kind and its
        staged polls stay promotable. A version that cannot be read is skipped; one id given two kinds stops the run
        (changing a kind would give existing items new keys)."""
        kinds: dict[str, str] = {}
        for version, data in self.files.every_version():
            try:
                listed = parse_feed_list(data, version) if data is not None else None
            except FeedListError:
                continue
            for feed in listed.feeds if listed else ():
                if kinds.setdefault(feed.feed_id, feed.kind) != feed.kind:
                    raise FeedListError(codes.FEED_KIND_CHANGED)
        if not kinds:
            raise FeedListError(codes.FEED_LIST_MISSING)
        return kinds
