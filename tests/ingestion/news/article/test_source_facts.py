"""NP2a: where an article came from, as facts. The tier and other judgements are NOT in the file (computed on read)."""

from __future__ import annotations

import json

import pytest

from fno.ingestion.news.article.article_file import FORMAT, Article, article_from_bytes, build_article
from fno.ingestion.news.article.keys import PUBLISHER, WRAPPER
from fno.ingestion.news.article.parse_feed import parse_poll
from fno.ingestion.news.article.read_poll import read_poll
from tests.ingestion.news.article.samples import SEEN, rss, rss_item


def built(kind, **item):
    return read_poll(rss(rss_item(**item)), kind, SEEN).articles[0]


def test_a_publisher_item_with_an_https_link_has_that_link_as_its_source():
    article = built(PUBLISHER, link="https://www.pub.example/a/1?utm_source=x")
    assert (article.source_domain, article.source_url, article.url_status) == (
        "www.pub.example", "https://www.pub.example/a/1", "publisher")  # fmt: skip


@pytest.mark.parametrize(
    "link",
    [
        "http://pub.example/a/1",
        "ftp://pub.example/a",
        "https://pub.example:8443/a",
        "",
    ],
)
def test_a_publisher_item_without_a_usable_https_link_has_no_source(link):
    article = built(PUBLISHER, link=link, guid="g-1")
    assert (article.source_domain, article.source_url, article.url_status) == ("", "", "none")


def test_a_google_news_item_takes_the_outlet_host_from_its_source_element_and_leaves_the_url_empty():
    article = built(
        WRAPPER,
        link="https://news.google.com/rss/articles/CBMiabc?oc=5",
        guid="g-2",
        source="Outlet Daily",
        source_url="https://outlet.example",
    )
    assert (article.source_domain, article.source_url, article.url_status) == ("outlet.example", "", "undecoded")
    assert article.canonical_url == ""  # unchanged: the wrapper link is never stored as a canonical URL


@pytest.mark.parametrize(
    "claimed",
    [
        "",
        "http://outlet.example",
        "https://user@outlet.example",
        "https://outlet.example:81",
        "javascript:alert(1)",
        "https://x y.example",
        "https://[::1]",
    ],
)
def test_a_source_element_that_is_not_an_https_plain_host_gives_no_domain(claimed):
    article = built(
        WRAPPER, link="https://news.google.com/rss/articles/CBMiabc", guid="g-3", source="Outlet", source_url=claimed
    )
    assert article.source_domain == "" and article.url_status == "undecoded"


def test_the_parser_reads_the_source_url_attribute_and_not_the_link_into_it():
    (item,) = parse_poll(
        rss(rss_item(source="Outlet", source_url="https://outlet.example", link="https://pub.example/a"))
    )
    assert (
        item.source == "Outlet" and item.source_url == "https://outlet.example" and item.link == "https://pub.example/a"
    )


def test_a_new_article_file_is_format_2_and_round_trips_with_its_source_facts():
    article = built(
        WRAPPER,
        link="https://news.google.com/rss/articles/CBMiabc",
        guid="g-4",
        source="Outlet",
        source_url="https://outlet.example",
    )
    document = json.loads(article.to_bytes())
    assert document["format"] == FORMAT == 2 and document["source_domain"] == "outlet.example"
    assert article_from_bytes(article.to_bytes()) == article


def test_no_tier_wire_or_promotional_judgement_is_written_into_an_article_file():
    document = json.loads(built(PUBLISHER).to_bytes())
    assert not {"tier", "origin_wire", "promotional", "tickers", "priority"} & set(document)


def test_a_format_1_file_is_still_read_with_empty_source_facts():
    v1 = {
        "format": 1, "key": "k" * 64, "kind": "publisher", "source": "S", "title": "T", "summary": "",
        "canonical_url": "https://pub.example/a", "published_at": "", "time_source": "none",
        "first_seen_at": "2026-10-27T03:00:00+00:00",
    }  # fmt: skip
    article = article_from_bytes(json.dumps(v1).encode())
    assert isinstance(article, Article) and (article.source_domain, article.source_url, article.url_status) == (
        "",
        "",
        "",
    )


@pytest.mark.parametrize(
    "bad",
    [b"not json", b"[]", b"{}", json.dumps({"format": 3}).encode(), json.dumps({"format": 2, "key": "k"}).encode()],
)
def test_an_unknown_format_a_missing_key_or_text_that_is_not_an_article_is_refused(bad):
    with pytest.raises(ValueError):
        article_from_bytes(bad)


def test_an_unknown_extra_key_is_refused_so_a_future_field_is_never_silently_dropped():
    document = json.loads(built(PUBLISHER).to_bytes())
    document["surprise"] = "x"
    with pytest.raises(ValueError):
        article_from_bytes(json.dumps(document).encode())


def test_build_article_is_pure_over_its_inputs():
    (item,) = parse_poll(rss(rss_item(link="https://pub.example/a/9")))
    assert build_article(PUBLISHER, item, SEEN) == build_article(PUBLISHER, item, SEEN)


def test_credentials_in_a_publisher_link_are_dropped_by_the_canonical_form_and_never_stored():
    article = built(PUBLISHER, link="https://user:secret@pub.example/a/1")
    assert article.source_url == "https://pub.example/a/1" and "secret" not in article.to_bytes().decode()
