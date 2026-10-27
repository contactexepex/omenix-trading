"""NP1: the questions the news source rules answer, on a small hand-made rule set (no file, no network)."""

from __future__ import annotations

import pytest

from fno.ingestion.news.sources.loader import build_source_rules
from fno.ingestion.news.sources.rules import plain_host

RULES = build_source_rules({
    "domains": {
        "reuters.com": {"tier": "tier1", "names": ["Reuters"], "fetch": False},
        "economictimes.indiatimes.com": {"tier": "tier1", "names": ["The Economic Times", "ET Markets"]},
        "economictimes.com": {"tier": "tier1", "same_as": "economictimes.indiatimes.com"},
        "livemint.com": {"tier": "tier1", "names": ["Mint"]},
        "businesswire.com": {"tier": "primary", "https_links": True},
        "seekingalpha.com": {"tier": "tier2", "opinion_unless_path": "/news/"},
        "nseindia.com": {"tier": "primary"},
        "marketwatch.com": {"tier": "tier1", "fetch": False},
    },
    "wires": {"Reuters": {"names": ["Reuters Staff"], "domains": ["reuters.com"]}},
    "promotional": {"providers": ["Zacks"], "domains": ["zacks.com"], "text": ["sponsored content"]},
})  # fmt: skip


def test_a_host_finds_its_outlet_and_its_parent_domains_do_too():
    assert RULES.lookup("livemint.com").domain == "livemint.com"
    assert RULES.lookup("www.livemint.com").domain == "livemint.com"
    assert RULES.lookup("bfsi.economictimes.indiatimes.com").domain == "economictimes.indiatimes.com"
    assert RULES.lookup("LIVEMINT.COM.").domain == "livemint.com"  # case and a trailing dot do not matter


@pytest.mark.parametrize(
    "host",
    [
        "notreuters.com",  # a longer name that merely ends the same way
        "evil-reuters.com",
        "reuters.com.evil.example",  # the listed name in the middle
        "reuters.co",
        "x y.reuters.com",  # a space: not a host at all
        " reuters.com",  # whitespace at either end is not trimmed: it is not a host
        "reuters.com ",
        "reuters.com\n\n",
        "reuters.com\n",
        "\treuters.com",
        "reuters.com\u2028",
        "mar\u212aetwatch.com",  # the Kelvin sign: lower-casing would turn it into an ASCII k
        "user@reuters.com",
        "reuters.com:8080",
        "reuters.com/news",
        "rëuters.com",
        "127.0.0.1",
        "",
        None,
    ],
)
def test_a_look_alike_or_a_malformed_host_is_unlisted(host):
    assert RULES.lookup(host) is None and not RULES.may_fetch(host)


def test_an_unlisted_host_is_never_fetchable_and_an_outlet_that_refuses_bots_is_not_either():
    assert RULES.may_fetch("livemint.com") and RULES.may_fetch("nseindia.com")
    assert not RULES.may_fetch("reuters.com") and not RULES.may_fetch(
        "uk.reuters.com"
    )  # fetch: false, inherited by subdomains
    assert not RULES.may_fetch("unknown-blog.example")


def test_an_alias_of_an_outlet_that_refuses_bots_refuses_them_too():
    rules = build_source_rules({"domains": {
        "main.example": {"tier": "tier1", "fetch": False},
        "alias.example": {"tier": "tier1", "same_as": "main.example"},  # no fetch flag of its own
        "open.example": {"tier": "tier1"},
        "open-alias.example": {"tier": "tier1", "same_as": "open.example"},
    }})  # fmt: skip
    assert (
        not rules.may_fetch("main.example")
        and not rules.may_fetch("alias.example")
        and not rules.may_fetch("x.alias.example")
    )
    assert rules.may_fetch("open.example") and rules.may_fetch("open-alias.example")


def test_a_host_with_a_trailing_line_break_is_not_passed_on_by_plain_host():
    for host in ("marketwatch.com\n", "example.org\n", "example.org\r\n", "example.org\n\n"):
        assert RULES.lookup(host) is None and plain_host(host) == ""
