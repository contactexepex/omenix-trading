"""One news fetch run (P2a): the newest feed list, then every feed once. A feed list that cannot be used stops the run
with its fixed code before any request is sent."""

from __future__ import annotations

from fno.ingestion.news.feeds import PrivateFeedLists
from fno.ingestion.news.fetcher import FetchReport, NewsFetcher
from fno.ingestion.news.snapshot_log import NewsSnapshotLog


class NewsFetchJob:
    def __init__(self, lists: PrivateFeedLists, fetcher: NewsFetcher, log: NewsSnapshotLog):
        self.lists, self.fetcher, self.log = lists, fetcher, log

    def run(self) -> FetchReport:
        """Raises FeedListError (a fixed code) when the list is missing, invalid or older than one already used."""
        feeds = self.lists.latest(self.log.highest_feed_list_version(), self.log.used_feed_lists())
        return self.fetcher.run(feeds)
