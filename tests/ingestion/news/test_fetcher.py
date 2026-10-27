"""The news fetcher (P2a): raw bytes to Staging only, one poll-log row per saved poll, a fixed code for every outcome,
and one block stops the rest of its host for the run."""

from __future__ import annotations

import hashlib

import pytest
import requests

from fno.ingestion.news import codes
from fno.ingestion.news.feeds import parse_feed_list
from fno.ingestion.news.fetcher import SOURCE, NewsFetcher
from fno.ingestion.news.snapshot_log import NewsSnapshotLog
from fno.ingestion.promotion.staging import StagingArea
from fno.ingestion.storage.raw_store import LocalFolderStore
from fno.shared.nse_pacer import SourceCoolingOff
from tests.ingestion.news.fakes import CONSENT_PAGE, FEED_URL, NOW, OTHER_URL, RSS, Reply, Session, feed_list_bytes


class Spy(LocalFolderStore):
    def __init__(self, folder):
        super().__init__(folder)
        self.saved = []

    def put(self, path, data):
        self.saved.append(path)
        super().put(path, data)


def make(tmp_path, session):
    store, log = Spy(tmp_path / "drive"), NewsSnapshotLog(tmp_path / "repo")
    return NewsFetcher(session, StagingArea(store), log, lambda: NOW), store, log


def feeds(*urls, version=3):
    return parse_feed_list(feed_list_bytes(*urls), version)


def test_a_feed_is_staged_once_with_a_log_row_of_ids_and_hashes_only(tmp_path):
    fetcher, store, log = make(tmp_path, Session(**{FEED_URL: Reply()}))
    report = fetcher.run(feeds(FEED_URL))
    assert report.counts == {codes.FETCHED: 1} and report.ok
    assert store.saved == ["news/feed-01/2026/10/27/poll/20261027T030000Z"]
    (row,) = log.log.rows()
    assert row["feed_id"] == "feed-01" and row["sha256"] == hashlib.sha256(RSS).hexdigest()
    assert row["size_bytes"] == str(len(RSS)) and row["feed_list_version"] == "3"
    assert log.highest_feed_list_version() == 3


def test_the_same_bytes_again_are_unchanged_with_no_new_copy_and_no_new_row(tmp_path):
    fetcher, store, log = make(tmp_path, Session(**{FEED_URL: Reply()}))
    fetcher.run(feeds(FEED_URL))
    again = fetcher.run(feeds(FEED_URL))
    assert again.counts == {codes.UNCHANGED: 1} and again.ok
    assert len(store.saved) == 1 and len(log.log.rows()) == 1


def test_a_block_stops_the_rest_of_that_host_and_other_hosts_go_on(tmp_path):
    same_host = FEED_URL + "&second=1"
    session = Session(**{FEED_URL: Reply(200, CONSENT_PAGE), same_host: Reply(), OTHER_URL: Reply()})
    fetcher, store, _ = make(tmp_path, session)
    report = fetcher.run(feeds(FEED_URL, same_host, OTHER_URL))
    assert report.counts == {codes.BLOCK_PAGE: 1, codes.HOST_BLOCKED: 1, codes.FETCHED: 1} and not report.ok
    assert session.asked == [FEED_URL, OTHER_URL]  # the second feed of the blocked host is not asked
    assert len(store.saved) == 1


@pytest.mark.parametrize(
    ("reply", "code"),
    [
        (Reply(302, redirect=True), codes.BLOCK_PAGE),
        (Reply(429), codes.REFUSED),
        (Reply(403), codes.REFUSED),
        (Reply(503), codes.FETCH_FAILED),
        (requests.ConnectionError(f"could not reach {FEED_URL}"), codes.FETCH_FAILED),
        (SourceCoolingOff(f"{FEED_URL} refused"), codes.HOST_PAUSED),
    ],
)
def test_each_outcome_has_its_fixed_code_and_stages_nothing(tmp_path, reply, code):
    fetcher, store, log = make(tmp_path, Session(**{FEED_URL: reply}))
    report = fetcher.run(feeds(FEED_URL))
    assert report.counts == {code: 1} and store.saved == [] and log.log.rows() == []


def test_a_staging_failure_leaves_no_log_row(tmp_path):
    fetcher, store, log = make(tmp_path, Session(**{FEED_URL: Reply()}))
    store.put = lambda path, data: (_ for _ in ()).throw(RuntimeError(f"drive refused {path} {FEED_URL}"))
    report = fetcher.run(feeds(FEED_URL))
    assert report.counts == {codes.STAGE_FAILED: 1} and log.log.rows() == []


def test_the_fetcher_writes_only_to_the_news_staging_area(tmp_path):
    fetcher, store, _ = make(tmp_path, Session(**{FEED_URL: Reply(), OTHER_URL: Reply()}))
    fetcher.run(feeds(FEED_URL, OTHER_URL))
    assert store.saved and all(path.startswith(f"{SOURCE}/") for path in store.saved)


def test_the_report_line_is_counts_by_code_only(tmp_path):
    fetcher, _, _ = make(tmp_path, Session(**{FEED_URL: Reply(), OTHER_URL: Reply(429)}))
    assert fetcher.run(feeds(FEED_URL, OTHER_URL)).line() == "news fetch: fetched 1, refused 1"
