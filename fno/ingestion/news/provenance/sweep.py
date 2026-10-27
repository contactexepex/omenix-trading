"""The provenance sweep (NP11): which feed found which article does not depend on the range a promotion run was asked
for. A routine daily `promote --from today --to today` never reaches yesterday's polls, and an IST day is not a UTC
day (IST day D spans UTC D-1 18:30 to D 18:30), so every CLOSED IST day that has no provenance file yet is read from
ALL staged polls of the two UTC days that cover it, for every feed in the list (judge 123 B1). The first run after
a day closes writes its file; a day with a file is not read again (a poll staged later goes in by the range pass)."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import timedelta

from fno.ingestion.news import codes
from fno.ingestion.news.article.parse_feed import PollRejected
from fno.ingestion.news.article.read_poll import read_poll
from fno.ingestion.news.fetcher import SOURCE
from fno.ingestion.news.provenance.model import day_of
from fno.ingestion.news.provenance.writer import ProvenanceCollector, ProvenanceWriter
from fno.ingestion.promotion.staging import StagingArea


class ProvenanceSweep:
    def __init__(
        self, staging: StagingArea, kinds: Mapping[str, str], seen: ProvenanceCollector, writer: ProvenanceWriter
    ):
        self.staging, self.kinds, self.seen, self.writer = staging, kinds, seen, writer

    def run(self, report) -> None:
        for day in self.writer.open_days(report):
            for feed in sorted(self.kinds):
                for utc_day in (day - timedelta(days=1), day):
                    for poll in self.staging.copies(SOURCE, f"{feed}/{utc_day:%Y/%m/%d}/poll"):
                        if day_of(poll.fetched_at) == day and self.seen.first_look(poll):
                            self._look(feed, poll, report)

    def _look(self, feed: str, poll, report) -> None:
        try:
            reading = read_poll(poll.data, self.kinds[feed], poll.fetched_at)
        except PollRejected:
            report.reject(codes.PROVENANCE_POLL_SKIPPED)
            return
        self.seen.add(feed, poll.fetched_at, [article.key for article in reading.articles])
