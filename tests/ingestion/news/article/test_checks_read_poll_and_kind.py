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


# ---- judge 46 K1: an unreadable item must not take the others with it ----------------------------------------


@pytest.mark.parametrize(
    "bad_link",
    ["https://x.example:abc/a", "https://[::1/a", "https://x.example:99999999/a"],
    ids=["port", "ipv6", "range"],
)
def test_an_unreadable_link_is_one_counted_item_and_the_polls_good_items_survive(bad_link):
    poll = rss(
        rss_item(title="Good before", link="https://p.example/1"),
        rss_item(title="Bad link", link=bad_link),
        rss_item(title="Good after", link="https://p.example/2"),
    )
    reading = read_poll(poll, PUBLISHER, SEEN)
    assert [a.title for a in reading.articles] == ["Good before", "Good after"]
    assert reading.rejected == Counter({codes.ITEM_UNREADABLE: 1}) and reading.items == 3


def test_a_wrapper_item_does_not_need_its_link_so_a_bad_link_does_not_cost_it_the_article():
    poll = rss(rss_item(title="W", link="https://[::1/a", guid="gn-1"))
    assert [a.title for a in read_poll(poll, WRAPPER, SEEN).articles] == ["W"]


@pytest.mark.parametrize(
    "pub",
    [
        "0001-01-01T00:00:00+05:00",
        "9999-12-31T23:59:59-05:00",
        "Mon, 01 Jan 0001 00:00:00 +0500",
        "1850-01-01T00:00:00Z",
    ],
)
def test_an_impossible_or_implausible_time_is_no_time_and_the_item_is_kept(pub):
    from fno.ingestion.news.article.times import SEEN as SEEN_SOURCE
    from fno.ingestion.news.article.times import parse_time

    assert parse_time(pub) == (None, SEEN_SOURCE)  # no OverflowError, no accidental year 2001
    (article,) = read_poll(rss(rss_item(pub=pub)), PUBLISHER, SEEN).articles
    assert article.published_at == "" and article.time_source == SEEN_SOURCE


# ---- judge 46 K2: every part of the Google News fallback key matters on its own -------------------------------

SAME = dict(title="Stocks to watch", summary="s", source="Outlet")


@pytest.mark.parametrize(
    "different",
    [dict(title="Another headline"), dict(summary="another summary"), dict(source="Another outlet")],
    ids=["title", "summary", "source"],
)
def test_with_the_same_time_one_differing_text_part_alone_gives_a_different_wrapper_key(different):
    from datetime import UTC, datetime

    from fno.ingestion.news.article.keys import item_key

    moment = datetime(2026, 10, 27, 2, 30, 0, tzinfo=UTC)
    base = item_key(WRAPPER, RawItem(link="https://w.example/r", **SAME), moment)
    assert item_key(WRAPPER, RawItem(link="https://w.example/r", **{**SAME, **different}), moment) != base


# ---- the hostile-item inputs through the privacy surfaces (orchestrator guardrail) -------------------------


def test_no_fragment_of_a_bad_link_escapes_through_any_surface_at_debug(caplog, capsys):
    import logging

    caplog.set_level(logging.DEBUG)
    marks = ("MARKPORTZZ91", "MARKV6ZZ92", "MARKRANGEZZ93", "MARKTITLEZZ94")
    poll = rss(
        rss_item(title=marks[3], link=f"https://x.example:abc/{marks[0]}?q={marks[0]}"),
        rss_item(title=marks[3] + "2", link=f"https://[::1/{marks[1]}"),
        rss_item(title=marks[3] + "3", link=f"https://x.example:99999999/{marks[2]}"),
        rss_item(title="Good", link="https://p.example/ok"),
    )
    reading = read_poll(poll, PUBLISHER, SEEN)
    surfaces = repr(reading.rejected) + " ".join(reading.rejected) + caplog.text + capsys.readouterr().out
    assert (
        reading.rejected == Counter({codes.ITEM_UNREADABLE: 3}) and reading.items == 4
    )  # reconciliation still balances
    assert [a.title for a in reading.articles] == ["Good"]
    assert not [m for m in marks if m in surfaces]


# ---- the item_unreadable catch is narrow: our own defects are never counted as skipped items ----------------


def test_a_defect_in_the_article_build_propagates_and_is_not_counted_as_an_unreadable_item(monkeypatch):
    from fno.ingestion.news.article import article_file

    def defect(*args, **kwargs):
        raise ValueError("a bug in our own code")  # even a ValueError, the type a bad link raises

    monkeypatch.setattr(article_file, "item_key", defect)
    with pytest.raises(ValueError, match="a bug in our own code"):
        read_poll(rss(rss_item()), PUBLISHER, SEEN)


def test_the_unreadable_link_error_carries_no_part_of_the_link():
    from fno.ingestion.news.article.canonical import UnreadableLink, canonical_url

    with pytest.raises(UnreadableLink) as bad:
        canonical_url("https://x.example:abc/MARKSECRETZZ95")
    assert "MARKSECRETZZ95" not in str(bad.value) + repr(bad.value) and bad.value.__cause__ is None
