"""The news promotion gate (P2b2): staged polls -> articles -> the Record. It reads Staging and writes only through the
ArticleWriter; a poll that fails stays in Staging with its fixed code (never pruned, re-read on every run). Re-running a
range is safe: an article already recorded is a no-op."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from datetime import date, timedelta

from fno.ingestion.news import codes
from fno.ingestion.news.article.parse_feed import PollRejected
from fno.ingestion.news.article.read_poll import read_poll
from fno.ingestion.news.fetcher import SOURCE
from fno.ingestion.news.record.report import NO_OPS, RECORDED, REVISIONS, PromotionReport
from fno.ingestion.news.record.writer import ArticleWriter, Outcome
from fno.ingestion.promotion.staging import StagedCopy, StagingArea
from fno.ingestion.storage.raw_store import RawFileConflict

COUNTED = {Outcome.RECORDED: RECORDED, Outcome.REVISION: REVISIONS, Outcome.NO_OP: NO_OPS}


def days_between(start: date, end: date) -> list[date]:
    return [start + timedelta(days=n) for n in range((end - start).days + 1)]


class NewsGate:
    def __init__(self, staging: StagingArea, writer: ArticleWriter, kinds: Mapping[str, str]):
        """`kinds`: feed id -> item kind, from the private feed list. Staging is read only."""
        self.staging, self.writer, self.kinds = staging, writer, kinds

    def promote(self, start: date, end: date) -> PromotionReport:
        report = PromotionReport()
        days = days_between(start, end)
        for feed in self.staging.children(SOURCE):
            if feed not in self.kinds and self._staged_in(feed, days):
                # no kind, so no key: left staged, never guessed. Only polls in the range count, so a feed
                # dropped from the list stops being reported once its days are out of the range.
                report.reject(codes.FEED_UNKNOWN)
        for feed in sorted(self.kinds):
            for day in days:
                for poll in self._polls(feed, day):
                    self._poll(poll, self.kinds[feed], report)
        return report

    def _polls(self, feed: str, day: date) -> list[StagedCopy]:
        return self.staging.copies(SOURCE, f"{feed}/{day:%Y/%m/%d}/poll")

    def _staged_in(self, feed: str, days: list[date]) -> bool:
        return any(self._polls(feed, day) for day in days)

    def _poll(self, poll: StagedCopy, kind: str, report: PromotionReport) -> None:
        try:
            reading = read_poll(poll.data, kind, poll.fetched_at)
        except PollRejected as refused:
            report.reject(str(refused))
            return
        outcomes, failed = Counter(), 0
        for article in reading.articles:
            try:
                outcomes[COUNTED[self.writer.write(article, poll.fetched_at.date())]] += 1
            except RawFileConflict:
                report.reject(codes.RECORD_CONFLICT)
                failed += 1
            except Exception:  # noqa: BLE001 - Drive's own errors may name paths; only the code is kept
                report.reject(codes.RECORD_FAILED)
                failed += 1
        for code, number in reading.rejected.items():
            report.reject(code, number)
        report.poll_done(reading.items, outcomes, failed, sum(reading.rejected.values()))
