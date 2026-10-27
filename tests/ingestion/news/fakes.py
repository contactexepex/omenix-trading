"""Shared fakes of the news tests: no network, no Drive, no sleep. Every URL, query and headline here is a MARKER the
privacy test searches for; none is a real feed."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from fno.ingestion.news.feeds import FEEDS_FOLDER

MARK_QUERY = "MARKQUERYZZ41"
MARK_HEADLINE = "MARKHEADLINEZZ42"
MARK_HOST = "marker-host-zz43.example"
MARK_PATH = "MARKPATHZZ44"
MARKERS = (MARK_QUERY, MARK_HEADLINE, MARK_HOST, MARK_PATH)
FEED_URL = f"https://{MARK_HOST}/{MARK_PATH}/rss?q={MARK_QUERY}"
OTHER_URL = "https://other-host-zz45.example/rss"
NOW = datetime(2026, 10, 27, 3, 0, 0, tzinfo=UTC)

RSS = (
    f"<?xml version='1.0'?><rss version='2.0'><channel><item><title>{MARK_HEADLINE}</title></item></channel></rss>"
).encode()
CONSENT_PAGE = f"<html><body>consent {MARK_HEADLINE} {FEED_URL}</body></html>".encode()


SALT = "0123456789abcdef-salt"


def feed_list_bytes(*urls: str, salt: str = SALT) -> bytes:
    feeds = [{"id": f"feed-{n:02d}", "url": u} for n, u in enumerate(urls, start=1)]
    return json.dumps({"salt": salt, "feeds": feeds}).encode()


def put_version(store, version: int, *urls: str) -> None:
    store.put(f"{FEEDS_FOLDER}/feeds-v{version}.json", feed_list_bytes(*urls))


class Reply:
    def __init__(self, status=200, content=RSS, redirect=False):
        self.status_code, self.content, self.is_redirect = status, content, redirect


class Session:
    """Answers each URL from a script (an exception is raised); remembers the URLs asked."""

    def __init__(self, **by_url):
        self.by_url, self.asked = by_url, []

    def get(self, url, **kwargs):
        self.asked.append(url)
        step = self.by_url[url]
        if isinstance(step, BaseException):
            raise step
        return step
