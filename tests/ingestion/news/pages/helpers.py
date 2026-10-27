"""Builders of the NP4a tests: a fake session (nothing leaves the machine), invented hosts, a fake clock."""

from __future__ import annotations

import requests

from fno.ingestion.news.pages.fetcher import HttpsPageFetcher
from fno.ingestion.news.resolve.pacing import RequestSpacer
from fno.ingestion.news.sources.loader import build_source_rules

RULES = build_source_rules({"domains": {
    "pub.example": {"tier": "tier1"},
    "other.example": {"tier": "tier2"},
    "closed.example": {"tier": "tier1", "fetch": False},
    "in.closed.example": {"tier": "tier1"},  # a listed child of an outlet that refuses automated reads
}})  # fmt: skip
GLOBAL = {"pub.example": ["93.184.216.34"], "other.example": ["93.184.216.35"], "closed.example": ["93.184.216.36"]}


class FakeResponse:
    def __init__(self, status=200, headers=None, chunks=(b"<html>ok</html>",), url=""):
        self.status_code, self.headers, self.chunks, self.url = (
            status,
            {"content-type": "text/html", **(headers or {})},
            chunks,
            url,
        )

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def iter_content(self, size):
        yield from self.chunks


class FakeSession(requests.Session):
    """`routes`: url -> FakeResponse (or an exception); every request is recorded."""

    def __init__(self, routes=None):
        super().__init__()
        self.routes, self.requests = dict(routes or {}), []

    def get(self, url, **kwargs):
        self.requests.append((url, kwargs))
        answer = self.routes.get(url, FakeResponse(404, {"content-type": "text/plain"}, (b"",)))
        if isinstance(answer, Exception):
            raise answer
        return answer


class Clock:
    def __init__(self):
        self.now, self.sleeps = 0.0, []

    def time(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


def fetcher(routes=None, resolver=None, **kwargs) -> tuple[HttpsPageFetcher, FakeSession, Clock]:
    clock, session = Clock(), FakeSession(routes)
    spacer = RequestSpacer(clock=clock.time, sleep=clock.sleep)
    made = HttpsPageFetcher(RULES, spacer, session, resolver or (lambda host: GLOBAL.get(host, ["10.0.0.1"])), **kwargs)
    return made, session, clock


def urls(session: FakeSession) -> list[str]:
    return [url for url, _ in session.requests]
