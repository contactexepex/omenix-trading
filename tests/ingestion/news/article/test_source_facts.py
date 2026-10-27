"""NP2a: where an article came from, as facts. Tier and other judgements are NOT in the file (computed on read), and the
resolved URL is not either (it gets its own file later)."""

from __future__ import annotations

import json

import pytest

from fno.ingestion.news.article.article_file import FORMAT, Article, article_from_bytes, build_article
from fno.ingestion.news.article.keys import PUBLISHER, WRAPPER
from fno.ingestion.news.article.parse_feed import parse_poll
from fno.ingestion.news.article.read_poll import read_poll
from tests.ingestion.news.article.samples import SEEN, rss, rss_item

WRAP = "https://wrap.example/rss/articles/CBMiabc?oc=5"


def built(kind, **item):
    return read_poll(rss(rss_item(**item)), kind, SEEN).articles[0]


def test_a_publisher_item_has_the_host_of_its_https_link_as_its_source_domain_and_no_wrapper_link():
    article = built(PUBLISHER, link="https://www.pub.example/a/1?utm_source=x")
    assert (article.source_domain, article.wrapper_link) == ("www.pub.example", "")
    assert article.canonical_url == "https://www.pub.example/a/1"  # the publisher link stays where it always was


@pytest.mark.parametrize("link", ["http://pub.example/a/1", "ftp://pub.example/a", "https://pub.example:8443/a", ""])
def test_a_publisher_item_without_a_usable_https_link_has_no_source_domain(link):
    assert built(PUBLISHER, link=link, guid="g-1").source_domain == ""


def test_credentials_in_a_publisher_link_are_dropped_by_the_canonical_form_and_never_stored():
    article = built(PUBLISHER, link="https://user:secret@pub.example/a/1")
    assert article.canonical_url == "https://pub.example/a/1" and "secret" not in article.to_bytes().decode()


def test_a_google_news_item_takes_the_outlet_host_from_its_source_element_and_keeps_its_wrapper_link():
    article = built(WRAPPER, link=WRAP, guid="g-2", source="Outlet Daily", source_url="https://outlet.example")
    assert (article.source_domain, article.wrapper_link) == ("outlet.example", WRAP)
    assert article.canonical_url == ""  # the wrapper link is never stored as a canonical URL


@pytest.mark.parametrize(
    "claimed",
    ["", "http://outlet.example", "https://user@outlet.example", "https://outlet.example:81", "javascript:alert(1)",
     "https://x y.example", "https://[::1]"],
)  # fmt: skip
def test_a_source_element_that_is_not_an_https_plain_host_gives_no_domain(claimed):
    article = built(WRAPPER, link=WRAP, guid="g-3", source="Outlet", source_url=claimed)
    assert article.source_domain == ""


BAD_WRAPPER_LINKS = [
    "http://wrap.example/a", "ftp://wrap.example/a", "https://u:p@wrap.example/a", "https://wrap.example:8443/a",
    "https://wrap example/a",
]  # fmt: skip


@pytest.mark.parametrize("link", BAD_WRAPPER_LINKS)
def test_a_wrapper_link_that_is_not_a_plain_https_link_is_not_kept(link):
    assert built(WRAPPER, link=link, guid="g-5", source="Outlet").wrapper_link == ""


def test_the_wrapper_key_does_not_depend_on_the_link_or_the_source_facts():
    first = built(WRAPPER, link=WRAP, guid="same-guid", source="Outlet", source_url="https://outlet.example")
    other = built(
        WRAPPER,
        link="https://elsewhere.example/x",
        guid="same-guid",
        source="Outlet",
        source_url="https://other.example",
    )
    assert first.key == other.key


def test_the_parser_reads_the_source_url_attribute_and_not_the_link_into_it():
    (item,) = parse_poll(
        rss(rss_item(source="Outlet", source_url="https://outlet.example", link="https://pub.example/a"))
    )
    assert (
        item.source == "Outlet" and item.source_url == "https://outlet.example" and item.link == "https://pub.example/a"
    )


def test_a_new_article_file_is_format_2_and_round_trips():
    article = built(WRAPPER, link=WRAP, guid="g-6", source="Outlet", source_url="https://outlet.example")
    document = json.loads(article.to_bytes())
    assert document["format"] == FORMAT == 2 and document["source_domain"] == "outlet.example"
    assert article_from_bytes(article.to_bytes()) == article


def test_no_judgement_and_no_resolved_url_is_written_into_an_article_file():
    document = json.loads(built(PUBLISHER).to_bytes())
    assert not {"tier", "origin_wire", "promotional", "tickers", "priority", "source_url", "url_status"} & set(document)


def test_a_format_1_file_is_still_read_with_empty_source_facts():
    v1 = {
        "format": 1, "key": "k" * 64, "kind": "publisher", "source": "S", "title": "T", "summary": "",
        "canonical_url": "https://pub.example/a", "published_at": "", "time_source": "none",
        "first_seen_at": "2026-10-27T03:00:00+00:00",
    }  # fmt: skip
    article = article_from_bytes(json.dumps(v1).encode())
    assert isinstance(article, Article) and (article.source_domain, article.wrapper_link) == ("", "")


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


# ---- judge 73 B2: the redirect link is written once, so it is cleaned first ---------------------------------


@pytest.mark.parametrize(
    "link",
    ["https://a.example\n/x", "https://news.example/a\nb", "https://a.example/x y", "https://a.example/x\ty", "https://a.example:443/x",
     "https://a.example:8443/x", "https://a.example\\@b.example/x", "https://a.example/x\x00y", "https://a.example/\x7fx",
     "https://u@a.example/x", "ftp://a.example/x", "//a.example/x", "https://", "https://a.example /x"],
)  # fmt: skip
def test_a_redirect_link_with_whitespace_a_control_character_a_port_or_credentials_is_not_kept(link):
    from fno.ingestion.news.article.source_facts import clean_https_link

    assert clean_https_link(link) == ""


def test_a_redirect_link_is_kept_lower_cased_in_scheme_and_host_without_its_fragment_and_trimmed_at_the_ends():
    from fno.ingestion.news.article.source_facts import clean_https_link

    assert clean_https_link("HTTPS://A.Example/Path/X?Q=1&r=2#frag") == "https://a.example/Path/X?Q=1&r=2"
    assert clean_https_link("  https://a.example/x\n") == "https://a.example/x"


def test_what_the_article_file_stores_as_wrapper_link_is_the_cleaned_link():
    article = built(WRAPPER, link="HTTPS://WRAP.Example/rss/a?oc=5", guid="g-9", source="Outlet")
    assert article.wrapper_link == "https://wrap.example/rss/a?oc=5"
