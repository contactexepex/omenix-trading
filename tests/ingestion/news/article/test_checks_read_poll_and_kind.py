"""P2b1: item checks, one poll into articles with its counts, and the optional `kind` of a feed."""

from __future__ import annotations

import json
from collections import Counter

import pytest

from fno.ingestion.news import codes
from fno.ingestion.news.article.item_checks import MAX_FIELD_CHARS, item_refusal
from fno.ingestion.news.article.keys import PUBLISHER, WRAPPER
from fno.ingestion.news.article.parse_feed import PollRejected
from fno.ingestion.news.article.raw_item import RawItem
from fno.ingestion.news.article.read_poll import read_poll
from fno.ingestion.news.feeds import FeedListError, parse_feed_list
from tests.ingestion.news.article.samples import BILLION_LAUGHS, SEEN, rss, rss_item
from tests.ingestion.news.fakes import SALT


@pytest.mark.parametrize(
    ("item", "code"),
    [
        (RawItem(title="", link="https://p.example/1"), codes.ITEM_MISSING_TITLE),
        (RawItem(title="   ", link="https://p.example/1"), codes.ITEM_MISSING_TITLE),
        (RawItem(title="T"), codes.ITEM_MISSING_LINK),
        (RawItem(title="T", link=" ", guid=" "), codes.ITEM_MISSING_LINK),
        (RawItem(title="T", link="https://p.example/1", summary="x" * (MAX_FIELD_CHARS + 1)), codes.ITEM_TOO_LONG),
        (RawItem(title="T", guid="g-only"), None),  # a guid alone is enough
        (RawItem(title="T", link="https://p.example/1", summary="x" * MAX_FIELD_CHARS), None),
        (RawItem(title="T", link="https://p.example/1", published=""), None),  # no time is not a reason to refuse
    ],
)
def test_each_check_returns_its_fixed_code_or_none(item, code):
    assert MAX_FIELD_CHARS == 20_000
    assert item_refusal(item) == code


def test_a_poll_is_every_item_either_an_article_or_counted_by_its_code():
    poll = rss(
        rss_item(title="Good one", link="https://p.example/1"),
        rss_item(title="", link="https://p.example/2"),
        rss_item(title="No link", link="", guid=""),
        rss_item(title="Good two", link="https://p.example/3", pub=""),
        rss_item(
            title="Good one again", link="https://p.example/1?utm_source=x"
        ),  # the same article: both are returned
    )
    reading = read_poll(poll, PUBLISHER, SEEN)
    assert [a.title for a in reading.articles] == ["Good one", "Good two", "Good one again"]
    assert reading.rejected == Counter({codes.ITEM_MISSING_TITLE: 1, codes.ITEM_MISSING_LINK: 1})
    assert reading.items == 5  # the sum the writer reconciles against
    assert reading.articles[0].key == reading.articles[2].key  # the repeat is the writer's no-op, not lost here


def test_a_refused_poll_raises_its_code_and_no_item_is_read():
    with pytest.raises(PollRejected, match=codes.UNSAFE_XML):
        read_poll(BILLION_LAUGHS, PUBLISHER, SEEN)


def test_the_kind_of_a_poll_reaches_the_key_and_a_wrapper_article_keeps_no_url():
    poll = rss(rss_item(title="W", link="https://wrapper.example/r?x=1", guid="gn-1"))
    (wrapper,) = read_poll(poll, WRAPPER, SEEN).articles
    (publisher,) = read_poll(poll, PUBLISHER, SEEN).articles
    assert wrapper.key != publisher.key and wrapper.canonical_url == "" and publisher.canonical_url


# ---- the optional `kind` of a feed in the private list ---------------------------------------------------------


def listing(**feed):
    return json.dumps({"salt": SALT, "feeds": [{"id": "feed-01", "url": "https://h.example/x", **feed}]}).encode()


def test_a_feed_list_without_kind_still_loads_and_defaults_to_publisher():
    assert parse_feed_list(listing(), 1).feeds[0].kind == PUBLISHER


def test_the_wrapper_kind_is_accepted_and_any_other_is_refused():
    assert parse_feed_list(listing(kind="wrapper"), 1).feeds[0].kind == WRAPPER
    for bad in ("Publisher", "news", "", 3):
        with pytest.raises(FeedListError, match=codes.FEED_LIST_INVALID):
            parse_feed_list(listing(kind=bad), 1)


def test_nothing_the_gate_reports_carries_a_headline_or_url_only_codes_and_counts():
    marker_title, marker_url = "MARKHEADLINEZZ77", "https://marker-zz78.example/MARKPATHZZ79?q=MARKQUERYZZ80"
    poll = rss(rss_item(title="", link=marker_url, desc=marker_title), rss_item(title=marker_title, link="", guid=""))
    reading = read_poll(poll, PUBLISHER, SEEN)
    reported = " ".join(reading.rejected) + repr(dict(reading.rejected))
    hostile = BILLION_LAUGHS.replace(b"lolz", marker_title.encode())
    with pytest.raises(PollRejected) as refused:
        read_poll(hostile, PUBLISHER, SEEN)
    reported += str(refused.value) + repr(refused.value)
    assert not [m for m in (marker_title, marker_url, "MARKPATHZZ79", "MARKQUERYZZ80") if m in reported]
    assert set(reading.rejected) <= {codes.ITEM_MISSING_TITLE, codes.ITEM_MISSING_LINK}
