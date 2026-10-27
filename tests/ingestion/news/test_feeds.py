"""The private feed list (P2a, R1): write-once versions, the newest by number, a fixed code for every problem, and a URL
that no traceback or repr can print."""

from __future__ import annotations

import pytest

from fno.ingestion.news import codes
from fno.ingestion.news.feeds import FeedEntry, FeedListError, PrivateFeedLists, parse_feed_list
from fno.ingestion.storage.raw_store import LocalFolderStore
from tests.ingestion.news.fakes import FEED_URL, MARK_QUERY, OTHER_URL, feed_list_bytes, put_version


@pytest.fixture
def lists(tmp_path):
    store = LocalFolderStore(tmp_path)
    return store, PrivateFeedLists(store)


def test_the_newest_version_by_number_is_used_so_v10_beats_v9(lists):
    store, feeds = lists
    put_version(store, 9, FEED_URL)
    put_version(store, 10, FEED_URL, OTHER_URL)
    got = feeds.latest()
    assert got.version == 10 and [f.feed_id for f in got.feeds] == ["feed-01", "feed-02"]


def test_adding_a_version_is_picked_up_by_the_next_run_and_nothing_halts(lists):
    store, feeds = lists
    put_version(store, 1, FEED_URL)
    assert feeds.latest().version == 1
    put_version(store, 2, FEED_URL, OTHER_URL)
    assert feeds.latest(lowest_version=1).version == 2


def test_no_list_stops_with_a_code(lists):
    with pytest.raises(FeedListError, match=codes.FEED_LIST_MISSING):
        lists[1].latest()


def test_a_version_older_than_one_already_used_is_refused_no_rolling_back(lists):
    store, feeds = lists
    put_version(store, 2, FEED_URL)
    with pytest.raises(FeedListError, match=codes.FEED_LIST_ROLLED_BACK):
        feeds.latest(lowest_version=3)


@pytest.mark.parametrize(
    "data",
    [
        b"not json",
        b'{"feeds": []}',
        b'{"nofeeds": 1}',
        b'{"feeds": [{"id": "gn-nifty", "url": "https://h.example/x"}]}',  # an id that names a topic
        b'{"feeds": [{"id": "feed-01", "url": "http://h.example/x"}]}',  # not https
        b'{"feeds": [{"id": "feed-01", "url": "https://h.example/x"}, {"id": "feed-01", "url": "https://h.example/y"}]}',
        b'{"feeds": [{"id": "feed-01"}]}',
    ],
)
def test_an_unusable_list_is_refused_with_the_fixed_code_and_no_text(data):
    with pytest.raises(FeedListError) as refused:
        parse_feed_list(data, 1)
    assert str(refused.value) == codes.FEED_LIST_INVALID and refused.value.__cause__ is None


def test_a_feed_entry_never_prints_its_url():
    entry = FeedEntry("feed-01", FEED_URL)
    assert MARK_QUERY not in repr(entry) and MARK_QUERY not in str(entry)
    assert parse_feed_list(feed_list_bytes(FEED_URL), 1).feeds[0].host == "marker-host-zz43.example"
