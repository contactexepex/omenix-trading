"""NP1: the questions the news source rules answer, on a small hand-made rule set (no file, no network)."""

from __future__ import annotations

import pytest

from fno.ingestion.news.sources.loader import build_source_rules

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
    assert RULES.tier_of("livemint.com") == "tier1"
    assert RULES.tier_of("www.livemint.com") == "tier1"
    assert RULES.tier_of("bfsi.economictimes.indiatimes.com") == "tier1"
    assert RULES.tier_of("LIVEMINT.COM.") == "tier1"  # case and a trailing dot do not matter


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
    assert RULES.lookup(host) is None and RULES.tier_of(host) == "unlisted" and not RULES.may_fetch(host)


def test_an_unlisted_host_is_never_fetchable_and_an_outlet_that_refuses_bots_is_not_either():
    assert RULES.may_fetch("livemint.com") and RULES.may_fetch("nseindia.com")
    assert not RULES.may_fetch("reuters.com") and not RULES.may_fetch(
        "uk.reuters.com"
    )  # fetch: false, inherited by subdomains
    assert not RULES.may_fetch("unknown-blog.example")


def test_two_hosts_of_one_outlet_have_one_key_and_an_unlisted_host_loses_only_its_prefixes():
    assert RULES.outlet_key("m.economictimes.com") == "economictimes.indiatimes.com"
    assert RULES.outlet_key("economictimes.indiatimes.com") == "economictimes.indiatimes.com"
    assert RULES.outlet_key("www.example.org") == "example.org"
    assert RULES.outlet_key("amp.m.example.org") == "example.org"
    assert RULES.outlet_key("blog.example.org") == "blog.example.org"
    assert RULES.outlet_key("not a host") == ""


def test_only_a_listed_https_links_outlet_may_have_an_http_link_upgraded():
    assert RULES.may_upgrade_to_https("businesswire.com") and RULES.may_upgrade_to_https("www.businesswire.com")
    assert not RULES.may_upgrade_to_https("livemint.com") and not RULES.may_upgrade_to_https("example.org")


def test_a_news_desk_prefix_decides_opinion_and_an_unknown_path_is_opinion():
    assert not RULES.is_opinion("seekingalpha.com", "/news/some-story")
    assert RULES.is_opinion("seekingalpha.com", "/article/some-post")
    assert RULES.is_opinion("seekingalpha.com", None)
    assert not RULES.is_opinion("livemint.com", "/anything") and not RULES.is_opinion("example.org", None)


def test_a_label_finds_its_domain_by_name_or_because_it_is_a_listed_host():
    assert RULES.domain_of_label("ET Markets") == "economictimes.indiatimes.com"
    assert RULES.domain_of_label("  the   economic times ") == "economictimes.indiatimes.com"
    assert RULES.domain_of_label("livemint.com") == "livemint.com"
    assert RULES.domain_of_label("m.economictimes.com") == "economictimes.com"
    assert RULES.domain_of_label("Some Unknown Daily") is None and RULES.domain_of_label("unknown-blog.example") is None
    assert RULES.domain_of_label(None) is None


def test_wire_and_promotional_lookups():
    assert RULES.wire_of_name("Reuters Staff") == "Reuters" and RULES.wire_of_name("reuters") == "Reuters"
    assert RULES.wire_of_name("Somebody Else") is None and RULES.wire_of_name(None) is None
    assert RULES.wire_of_domain("uk.reuters.com") == "Reuters" and RULES.wire_of_domain("notreuters.com") is None
    assert RULES.is_promotional_provider("ZACKS") and not RULES.is_promotional_provider("Mint")
    assert RULES.is_promotional_domain("www.zacks.com") and not RULES.is_promotional_domain("notzacks.com")


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


def test_an_empty_label_or_name_names_nothing_even_if_the_rules_were_built_with_one():
    from fno.ingestion.news.sources.model import Outlet, Promotional, Wire
    from fno.ingestion.news.sources.rules import SourceRules

    # the loader refuses such a name (see test_loader); the lookups must still never match it
    outlets = {"a.example": Outlet("a.example", "tier1", names=(".",))}
    sloppy = SourceRules(outlets, (Wire("W", names=(".",)),), Promotional(providers=(".",)))
    for rules in (RULES, sloppy):
        for value in (None, "", " ", ".", "..."):
            assert rules.domain_of_label(value) is None
            assert rules.wire_of_name(value) is None
            assert not rules.is_promotional_provider(value)


def test_the_news_desk_prefix_must_match_at_a_slash_boundary():
    assert RULES.is_opinion("seekingalpha.com", "/newsletter/today") and RULES.is_opinion("seekingalpha.com", "/news")
    assert not RULES.is_opinion("seekingalpha.com", "/news/today")
