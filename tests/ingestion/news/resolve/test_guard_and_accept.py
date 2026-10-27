"""NP2b: where the resolver may call, and what it may keep. The allowed domain comes from the private feed list only."""

from __future__ import annotations

import pytest

from fno.ingestion.news.feeds import FeedEntry
from fno.ingestion.news.resolve.accept import accept
from fno.ingestion.news.resolve.guard import EgressGuard, guard_from_feeds, registrable_domain
from fno.ingestion.news.resolve.model import BAD_RESULT, RESOLVED

GUARD = EgressGuard(["svc.example"])


def feed(feed_id: str, host: str, kind: str) -> FeedEntry:
    return FeedEntry(feed_id, f"https://{host}/rss/search?q=zzmarker", kind)


def test_the_allowed_domains_are_the_registrable_domains_of_the_wrapper_feeds_only():
    guard = guard_from_feeds([
        feed("feed-01", "news.svc.example", "wrapper"),
        feed("feed-02", "feeds.pub.example", "publisher"),  # a publisher feed's host is never allowed
        feed("feed-03", "wrap.other.co.uk", "wrapper"),
    ])  # fmt: skip
    assert guard.allowed == {"svc.example", "other.co.uk"}
    assert guard.allows_host("a.b.svc.example") and not guard.allows_host("pub.example")


def test_no_wrapper_feed_means_nothing_is_allowed():
    guard = guard_from_feeds([feed("feed-01", "feeds.pub.example", "publisher")])
    assert (
        not guard
        and not guard.allows_host("feeds.pub.example")
        and not guard.allows_link("https://feeds.pub.example/a")
    )


REGISTRABLE = [
    ("news.svc.example", "svc.example"), ("svc.example", "svc.example"), ("a.b.c.org.uk", "c.org.uk"),
    ("x.co.in", "x.co.in"), ("co.in", ""), ("localhost", ""), ("", ""),
]  # fmt: skip


@pytest.mark.parametrize(("host", "domain"), REGISTRABLE)
def test_registrable_domain(host, domain):
    assert registrable_domain(host) == domain


@pytest.mark.parametrize(
    "link",
    ["http://news.svc.example/a", "https://news.svc.example:8443/a", "https://u:p@news.svc.example/a", "https://notsvc.example/a",
     "https://svc.example.evil.example/a", "https://evil.example/a?u=https://svc.example/", "//svc.example/a", "ftp://svc.example/a",
     "https://svc.example\n/a", "", "not a link", "https://news.svc.example/rss/articles/a\u200bb", "https://news.svc.example/rss/articles/\u00e9"],
)  # fmt: skip
def test_a_link_off_the_allowed_domain_or_not_plain_https_is_not_allowed(link):
    assert not GUARD.allows_link(link)


def test_an_https_link_on_the_allowed_domain_or_a_subdomain_is_allowed():
    assert GUARD.allows_link("https://news.svc.example/rss/articles/abc?oc=5") and GUARD.allows_link(
        "https://svc.example/x"
    )


def test_a_clean_publisher_url_is_kept():
    assert accept("https://www.Pub.Example/a/b?x=1#frag", GUARD) == accept("https://www.pub.example/a/b?x=1", GUARD)
    assert accept("https://www.pub.example/a/b?x=1", GUARD).code == RESOLVED
    assert accept("https://www.pub.example/a/b?x=1", GUARD).url == "https://www.pub.example/a/b?x=1"


@pytest.mark.parametrize(
    "decoded",
    [None, 5, b"https://pub.example/a", "", "  ", "http://pub.example/a", "https://pub.example/a b", "https://pub.example/a\nb",
     "https://u:p@pub.example/a", "https://pub.example:443/a", "javascript:alert(1)", "https://news.svc.example/read/abc",
     "https://svc.example/"],
)  # fmt: skip
def test_a_result_that_is_not_a_clean_https_publisher_link_is_a_bad_result(decoded):
    assert accept(decoded, GUARD).code == BAD_RESULT and accept(decoded, GUARD).url == ""
