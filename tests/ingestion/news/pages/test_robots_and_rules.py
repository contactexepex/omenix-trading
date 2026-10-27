"""NP4a: robots.txt through the same fetcher, and the rule that a refusing parent covers its listed children."""

from __future__ import annotations

import pytest

from fno.ingestion.news.pages import model
from fno.ingestion.news.sources.loader import build_source_rules, load_source_rules
from tests.ingestion.news.pages.helpers import FakeResponse, fetcher, urls

PAGE = "https://pub.example/private/story"
ROBOTS = "https://pub.example/robots.txt"


def robots(text: str, status: int = 200) -> dict:
    return {ROBOTS: FakeResponse(status, {"content-type": "text/plain"}, (text.encode(),))}


def test_a_path_robots_txt_disallows_is_not_requested():
    fetch, session, _ = fetcher({**robots("User-agent: *\nDisallow: /private/\n"), PAGE: FakeResponse()})
    assert fetch.fetch(PAGE).code == model.ROBOTS_DISALLOWED and PAGE not in urls(session)
    assert fetch.fetch("https://pub.example/public/story").code != model.ROBOTS_DISALLOWED


def test_a_rule_for_our_own_agent_token_is_honoured():
    fetch, session, _ = fetcher({**robots("User-agent: fno-desk\nDisallow: /\n"), PAGE: FakeResponse()})
    assert fetch.fetch(PAGE).code == model.ROBOTS_DISALLOWED and PAGE not in urls(session)


@pytest.mark.parametrize("status", [404, 410, 400, 418])
def test_a_missing_or_client_error_robots_txt_means_no_restriction(status):
    fetch, _, _ = fetcher({ROBOTS: FakeResponse(status), PAGE: FakeResponse()})
    assert fetch.fetch(PAGE).code == model.OK


@pytest.mark.parametrize("status", [500, 502])
def test_a_server_error_means_the_hosts_pages_are_not_read_this_run(status):
    fetch, session, _ = fetcher({ROBOTS: FakeResponse(status), PAGE: FakeResponse()})
    assert fetch.fetch(PAGE).code == model.ROBOTS_UNREADABLE and PAGE not in urls(session)


@pytest.mark.parametrize("status", [401, 403, 429, 503])
def test_a_refusal_of_robots_txt_stops_the_host_like_any_other_request(status):
    fetch, session, _ = fetcher({ROBOTS: FakeResponse(status), PAGE: FakeResponse()})
    assert fetch.fetch(PAGE).code == model.ROBOTS_UNREADABLE and "pub.example" in fetch.stopped
    assert fetch.fetch(PAGE).code == model.HOST_STOPPED and PAGE not in urls(session)


def test_robots_txt_is_read_once_per_host_per_run():
    fetch, session, _ = fetcher({**robots("User-agent: *\nAllow: /\n"), PAGE: FakeResponse()})
    fetch.fetch(PAGE)
    fetch.fetch("https://pub.example/other/story")
    assert urls(session).count(ROBOTS) == 1


def test_a_robots_txt_that_redirects_to_another_host_is_unreadable_and_that_host_is_not_asked():
    elsewhere = "https://other.example/robots.txt"
    fetch, session, _ = fetcher({ROBOTS: FakeResponse(302, {"location": elsewhere}), PAGE: FakeResponse()})
    assert fetch.fetch(PAGE).code == model.ROBOTS_UNREADABLE and elsewhere not in urls(session)


def test_a_robots_txt_that_redirects_within_the_host_is_followed():
    moved = "https://pub.example/rules.txt"
    routes = {
        ROBOTS: FakeResponse(301, {"location": moved}),
        moved: robots("User-agent: *\nDisallow: /private/\n")[ROBOTS],
    }
    fetch, _, _ = fetcher({**routes, PAGE: FakeResponse()})
    assert fetch.fetch(PAGE).code == model.ROBOTS_DISALLOWED


def test_robots_txt_goes_through_the_address_check_too():
    fetch, session, _ = fetcher(
        {**robots("User-agent: *\nAllow: /\n"), PAGE: FakeResponse()}, resolver=lambda h: ["100.64.0.1"]
    )
    assert fetch.fetch(PAGE).code == model.BLOCKED_ADDRESS and session.requests == []


def test_an_oversized_robots_txt_is_unreadable():
    fetch, _, _ = fetcher({ROBOTS: FakeResponse(200, {"content-type": "text/plain"}, (b"#" * 400_000, b"#" * 400_000))})
    assert fetch.fetch(PAGE).code == model.ROBOTS_UNREADABLE


# ---- the allowlist rule (judge 84 F1) ---------------------------------------------------------------------------


RULES = build_source_rules({"domains": {
    "parent.example": {"tier": "tier1", "fetch": False},
    "child.parent.example": {"tier": "tier1"},
    "open.example": {"tier": "tier1"},
    "news.open.example": {"tier": "tier2"},
    "alias.example": {"tier": "tier1", "same_as": "parent.example"},
    "refused-child.open.example": {"tier": "tier2", "fetch": False},
}})  # fmt: skip


@pytest.mark.parametrize(
    ("host", "fetchable"),
    [
        ("open.example", True), ("www.open.example", True), ("news.open.example", True),
        ("parent.example", False), ("child.parent.example", False),  # a listed child of a fetch: false parent
        ("deep.child.parent.example", False), ("x.parent.example", False), ("alias.example", False),
        ("refused-child.open.example", False), ("unlisted.example", False), ("", False), (None, False),
    ],
)  # fmt: skip
def test_a_host_is_fetchable_only_when_every_listed_domain_it_sits_under_allows_it(host, fetchable):
    assert RULES.may_fetch(host) is fetchable


def test_the_shipped_allowlist_keeps_its_fetchable_set_under_the_stricter_rule():
    """The 112 shipped entries: no outlet changed from fetchable to not by the ancestor rule (checked once, pinned)."""
    rules = load_source_rules()
    refusing = {d for d, o in rules.outlets.items() if not o.fetch}
    assert len(rules.outlets) == 112 and len(refusing) == 11
    assert {d for d in rules.outlets if not rules.may_fetch(d)} == refusing
