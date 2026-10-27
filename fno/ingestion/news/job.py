"""One news fetch run (P2a): the newest feed list, then every feed once. A feed list that cannot be used stops the run
with its fixed code before any request is sent."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from fno.ingestion.news.feeds import PrivateFeedLists
from fno.ingestion.news.fetcher import FetchReport, NewsFetcher
from fno.ingestion.news.snapshot_log import NewsSnapshotLog


class NewsFetchJob:
    def __init__(self, lists: PrivateFeedLists, fetcher: NewsFetcher, log: NewsSnapshotLog,
                 clock: Callable[[], datetime], session=None):  # fmt: skip
        """`session`: when given, it is paced for this run's feed list (NP3b) before the first request."""
        self.lists, self.fetcher, self.log, self.clock, self.session = lists, fetcher, log, clock, session

    def run(self) -> FetchReport:
        """Raises FeedListError (a fixed code) when the list is missing, invalid or older than one already used."""
        feeds = self.lists.latest(self.log.highest_feed_list_version(), self.log.used_feed_lists())
        self.log.note_feed_list(feeds.version, feeds.sha256, self.clock())
        if self.session is not None:
            self.session.pace_for(feeds)
        return self.fetcher.run(feeds)
