"""The news fetcher (P2a): each feed once, the raw bytes to Staging, a fixed code for every outcome. It writes Staging
and its own poll log and nothing else; the Record is the gate's alone. One block (a redirect, a non-feed page, a
refusal, a paused host) stops the rest of that host for the run and is never retried another way."""

from __future__ import annotations

import hashlib
from collections import Counter
from collections.abc import Callable
from datetime import datetime

import requests

from fno.ingestion.news import codes
from fno.ingestion.news.feeds import FeedEntry, FeedList
from fno.ingestion.news.response_check import classify
from fno.ingestion.news.snapshot_log import NewsSnapshotLog, PollRow
from fno.ingestion.promotion.staging import StagingArea
from fno.shared.nse_pacer import SourceCoolingOff

SOURCE = "news"  # the source tag of every staged poll
TIMEOUT_SECONDS = 30


class FetchReport:
    def __init__(self) -> None:
        self.counts: Counter[str] = Counter()

    def add(self, code: str) -> None:
        self.counts[code] += 1

    @property
    def ok(self) -> bool:
        return all(code in codes.OK_CODES for code in self.counts)

    def line(self) -> str:
        """Counts by fixed code, e.g. `news fetch: fetched 8, block_page 1`; never a feed, a URL or a title."""
        return "news fetch: " + (", ".join(f"{c} {n}" for c, n in sorted(self.counts.items())) or "no feeds")


class NewsFetcher:
    def __init__(self, session: requests.Session, staging: StagingArea, log: NewsSnapshotLog,
                 clock: Callable[[], datetime]):  # fmt: skip
        self.session, self.staging, self.log, self.clock = session, staging, log, clock

    def run(self, feeds: FeedList) -> FetchReport:
        report, stopped = FetchReport(), set()
        for _ in feeds.damaged:  # a version edited after use was skipped: the run is not clean
            report.add(codes.FEED_LIST_DAMAGED)
        for feed in feeds.feeds:
            if feed.host in stopped:
                report.add(codes.HOST_BLOCKED)
                continue
            code = self._poll(feed, feeds)
            if code in codes.HOST_STOPS:
                stopped.add(feed.host)
            report.add(code)
        return report

    def _poll(self, feed: FeedEntry, feeds: FeedList) -> str:
        try:
            response = self.session.get(feed.url, timeout=TIMEOUT_SECONDS)
        except SourceCoolingOff:
            return codes.HOST_PAUSED
        except requests.RequestException:
            return codes.FETCH_FAILED  # the message can carry the URL: only the code is kept
        verdict = classify(response.status_code, response.is_redirect, response.content)
        return self._stage(feed, feeds, response.content) if verdict == codes.FETCHED else verdict

    def _stage(self, feed: FeedEntry, feeds: FeedList, data: bytes) -> str:
        fetched_at = self.clock()
        path = f"{feed.feed_id}/{fetched_at:%Y/%m/%d}/poll"
        try:
            staged = self.staging.stage(SOURCE, path, data, fetched_at)
        except Exception:  # noqa: BLE001 - Drive's own errors may name paths; only the code is kept
            return codes.STAGE_FAILED
        if not staged:
            return codes.UNCHANGED
        self.log.append(
            PollRow(fetched_at, feed.feed_id, path, hashlib.sha256(data).hexdigest(), len(data), feeds.version)
        )
        return codes.FETCHED
