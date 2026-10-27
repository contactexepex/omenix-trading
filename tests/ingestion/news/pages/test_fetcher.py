"""NP4a: the page fetcher against a fake session. Nothing is requested anywhere."""

from __future__ import annotations

import gzip
import io

import pytest
import requests
import urllib3

from fno.ingestion.news.pages import model
from fno.ingestion.news.pages.fetcher import MAX_HOPS, HttpsPageFetcher
from fno.ingestion.news.resolve.pacing import SPACING_SECONDS
from fno.shared.constants import RESEARCH_USER_AGENT
from tests.ingestion.news.pages.helpers import RULES, FakeResponse, fetcher, urls

PAGE = "https://pub.example/story/1"
ROBOTS = "https://pub.example/robots.txt"
ROBOTS_OK = {ROBOTS: FakeResponse(200, {"content-type": "text/plain"}, (b"User-agent: *\nAllow: /\n",))}


def test_a_listed_page_is_fetched_after_its_robots_txt_and_spaced_from_it():
    fetch, session, clock = fetcher({**ROBOTS_OK, PAGE: FakeResponse(200, chunks=(b"<html>a", b"b</html>"))})
    page = fetch.fetch(PAGE)
    assert page.code == model.OK and page.body == b"<html>ab</html>" and page.final_url == PAGE
    assert urls(session) == [ROBOTS, PAGE]
    assert clock.sleeps == [SPACING_SECONDS]  # at least 1.5 s between any two requests, robots.txt included


def test_every_request_is_https_without_redirects_with_a_timeout_and_the_polite_user_agent():
    fetch, session, _ = fetcher({**ROBOTS_OK, PAGE: FakeResponse()})
    fetch.fetch(PAGE)
    assert all(kw["allow_redirects"] is False and kw["timeout"] and kw["stream"] is True for _, kw in session.requests)
    assert session.headers["User-Agent"] == RESEARCH_USER_AGENT
    assert "verify" not in session.requests[0][1]  # TLS verification is never switched off


@pytest.mark.parametrize(
    "url",
    ["http://pub.example/a", "ftp://pub.example/a", "https://u:p@pub.example/a", "https://pub.example:8443/a",
     "https:///a", "https://pub .example/a", "pub.example/a", "https://pub.example\\@evil.example/", ""],
)  # fmt: skip
def test_a_url_that_is_not_plain_https_is_refused_before_any_request(url):
    fetch, session, _ = fetcher()
    assert fetch.fetch(url).code == model.URL_REFUSED and session.requests == []


@pytest.mark.parametrize(
    "url",
    ["https://unlisted.example/a", "https://closed.example/a", "https://www.closed.example/a",
     "https://in.closed.example/a"],  # a listed child of a fetch: false outlet (judge 84 F1)
)  # fmt: skip
def test_only_listed_outlets_that_allow_automated_reads_are_fetched(url):
    fetch, session, _ = fetcher()
    assert fetch.fetch(url).code == model.HOST_NOT_ALLOWED and session.requests == []


def test_a_name_that_resolves_to_a_non_global_address_is_refused_before_any_request():
    for answer in (["100.64.0.1"], ["93.184.216.34", "10.0.0.1"], ["64:ff9b::808:808"], []):
        fetch, session, _ = fetcher(resolver=lambda host, a=answer: a)
        assert fetch.fetch(PAGE).code == model.BLOCKED_ADDRESS and session.requests == []


def test_a_redirect_is_followed_by_hand_and_the_final_url_is_the_last_hop():
    moved = "https://other.example/moved"
    routes = {
        **ROBOTS_OK, PAGE: FakeResponse(301, {"location": moved}), moved: FakeResponse(),
        "https://other.example/robots.txt": FakeResponse(404),
    }  # fmt: skip
    fetch, session, _ = fetcher(routes)
    page = fetch.fetch(PAGE)
    assert (
        page.code == model.OK
        and page.final_url == moved
        and urls(session) == [ROBOTS, PAGE, "https://other.example/robots.txt", moved]
    )


@pytest.mark.parametrize("target", ["https://evil.example/x", "http://pub.example/x", "https://closed.example/x",
                                    "https://u@pub.example/x", "https://pub.example:81/x"])  # fmt: skip
def test_a_hop_that_leaves_the_rules_is_a_refused_redirect_and_is_never_requested(target):
    fetch, session, _ = fetcher({**ROBOTS_OK, PAGE: FakeResponse(302, {"location": target})})
    assert fetch.fetch(PAGE).code == model.REDIRECT_REFUSED and target not in urls(session)


def test_a_hop_to_an_address_that_is_not_global_is_refused():
    routes = {**ROBOTS_OK, PAGE: FakeResponse(302, {"location": "https://other.example/x"})}
    fetch, session, _ = fetcher(
        routes, resolver=lambda host: ["100.64.0.9"] if host == "other.example" else ["93.184.216.34"]
    )
    assert fetch.fetch(PAGE).code == model.REDIRECT_REFUSED and "https://other.example/x" not in urls(session)


def test_too_many_hops_and_a_redirect_without_a_location_are_refused():
    loop = {**ROBOTS_OK, PAGE: FakeResponse(302, {"location": PAGE})}
    fetch, session, _ = fetcher(loop)
    assert fetch.fetch(PAGE).code == model.REDIRECT_REFUSED and urls(session).count(PAGE) == MAX_HOPS + 1
    fetch, _, _ = fetcher({**ROBOTS_OK, PAGE: FakeResponse(302)})
    assert fetch.fetch(PAGE).code == model.REDIRECT_REFUSED


@pytest.mark.parametrize("status", [401, 403, 429, 503])
def test_a_refusal_stops_that_host_for_the_run_and_only_that_host(status):
    other = "https://other.example/a"
    routes = {
        **ROBOTS_OK,
        PAGE: FakeResponse(status),
        other: FakeResponse(),
        "https://other.example/robots.txt": FakeResponse(404),
    }
    fetch, session, _ = fetcher(routes)
    assert fetch.fetch(PAGE).code == model.REFUSED and "pub.example" in fetch.stopped
    before = len(session.requests)
    assert fetch.fetch(PAGE).code == model.HOST_STOPPED and len(session.requests) == before  # not asked again
    assert fetch.fetch(other).code == model.OK  # the other outlet goes on


def test_other_errors_do_not_stop_the_host():
    fetch, _, _ = fetcher({**ROBOTS_OK, PAGE: FakeResponse(500)})
    page = fetch.fetch(PAGE)
    assert page.code == model.HTTP_ERROR and page.status == 500 and not fetch.stopped


def test_a_body_over_the_cap_is_too_large_and_nothing_is_kept():
    fetch, _, _ = fetcher({**ROBOTS_OK, PAGE: FakeResponse(chunks=(b"x" * 600, b"x" * 600))}, max_bytes=1000)
    page = fetch.fetch(PAGE)
    assert page.code == model.TOO_LARGE and page.body == b""


def test_the_cap_counts_decoded_bytes_so_a_small_gzip_body_that_inflates_is_too_large():
    """judge 84: through a real `requests` response, whose `iter_content` decodes the content-encoding."""
    inflated = gzip.compress(b"<html>" + b"a" * 200_000 + b"</html>")
    assert len(inflated) < 5_000

    class Adapter(requests.adapters.HTTPAdapter):
        def send(self, request, **kwargs):
            raw = urllib3.response.HTTPResponse(
                body=io.BytesIO(inflated), status=200, preload_content=False,
                headers={"content-encoding": "gzip", "content-type": "text/html"},
            )  # fmt: skip
            return self.build_response(request, raw)

    fetch, session, _ = fetcher(max_bytes=100_000)
    session.get = lambda url, **kw: requests.Session.get(session, url, **kw)
    session.mount("https://", Adapter())
    session.routes = {}
    page = fetch._follow(PAGE, check_robots=False, limit=100_000, accept=("text/html",))
    assert page.code == model.TOO_LARGE


def test_only_html_is_accepted():
    fetch, _, _ = fetcher({**ROBOTS_OK, PAGE: FakeResponse(headers={"content-type": "application/pdf"})})
    assert fetch.fetch(PAGE).code == model.NOT_HTML
    fetch, _, _ = fetcher(
        {**ROBOTS_OK, PAGE: FakeResponse(headers={"content-type": "application/xhtml+xml; charset=utf-8"})}
    )
    assert fetch.fetch(PAGE).code == model.OK


def test_a_network_error_is_a_fixed_code_and_the_message_is_not_kept():
    fetch, _, _ = fetcher({**ROBOTS_OK, PAGE: requests.ConnectionError("https://pub.example/secret path failed")})
    page = fetch.fetch(PAGE)
    assert page.code == model.ERROR and "secret" not in repr(page)


def test_requests_are_spaced_across_hosts_not_per_host():
    other = "https://other.example/a"
    routes = {
        **ROBOTS_OK,
        PAGE: FakeResponse(),
        other: FakeResponse(),
        "https://other.example/robots.txt": FakeResponse(404),
    }
    fetch, _, clock = fetcher(routes)
    fetch.fetch(PAGE)
    fetch.fetch(other)
    assert len(clock.sleeps) == 3 and all(gap >= SPACING_SECONDS - 1e-9 for gap in clock.sleeps)  # 4 requests, 3 gaps


def test_a_page_never_shows_its_url_or_body_in_its_repr():
    fetch, _, _ = fetcher({**ROBOTS_OK, PAGE: FakeResponse(chunks=(b"<html>zzsecret</html>",))})
    assert "zzsecret" not in repr(fetch.fetch(PAGE)) and "story/1" not in repr(fetch.fetch(PAGE))


def test_the_fetcher_is_a_page_fetcher_and_keeps_no_cookies():
    from fno.ingestion.news.session import RejectAllCookies

    fetch, session, _ = fetcher()
    assert isinstance(fetch, model.PageFetcher) and isinstance(session.cookies._policy, RejectAllCookies)
    assert HttpsPageFetcher.__mro__[1] is model.PageFetcher and RULES.may_fetch("pub.example")


def test_the_session_takes_no_proxy_or_settings_from_the_environment():
    """judge 88: with trust_env on, a proxy variable could carry a hop the address check never saw."""
    _, session, _ = fetcher()
    assert session.trust_env is False
