"""NP2b round 2: our own pacing on EVERY request and our own stop on a refusal, against the REAL library on a mock
transport (nothing leaves the machine). Two judges reproduced that the library skips its wait after a failed request and
never stops: 10 links against a 503 gave 10 requests and 0 sleeps. The same set-up is the test here."""

from __future__ import annotations

import httpx
import pytest

from fno.ingestion.news.resolve.decoder_adapter import GoogleNewsDecoderResolver
from fno.ingestion.news.resolve.guard import EgressGuard
from fno.ingestion.news.resolve.model import DECODE_FAILED, PAUSED, REFUSED_LINK
from fno.ingestion.news.resolve.pacing import SPACING_SECONDS, PushbackStop, RequestPacer

# the REAL library requests its own fixed service host, so these tests (and only tests: the code names no host) allow it
GUARD = EgressGuard(["google.com"])


def link(n: int) -> str:
    return f"https://news.google.com/rss/articles/CBMi{n:04d}abcdefghij?oc=5"


class Clock:
    def __init__(self):
        self.now, self.sleeps = 0.0, []

    def time(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def resolver_on(handler, clock: Clock) -> tuple[GoogleNewsDecoderResolver, list]:
    """The real `GoogleDecoder`, its client swapped for one on a mock transport that records every request."""
    from googlenewsdecoder import GoogleDecoder

    seen: list = []

    def recording(request):
        seen.append(str(request.url))
        return handler(request)

    def factory(timeout, agent):
        decoder = GoogleDecoder(timeout=timeout, user_agent=agent)
        decoder.client = httpx.Client(transport=httpx.MockTransport(recording), follow_redirects=True)
        return decoder

    pacer = RequestPacer(clock=clock.time, sleep=clock.sleep)
    return GoogleNewsDecoderResolver(GUARD, pacer=pacer, decoder_factory=factory), seen


def test_a_plain_failure_is_still_paced_every_request_waits_even_when_the_one_before_failed():
    clock = Clock()
    resolver, seen = resolver_on(lambda request: httpx.Response(404, text="gone"), clock)  # not a pushback
    results = resolver.resolve([link(n) for n in range(10)])
    assert [r.code for r in results] == [DECODE_FAILED] * 10
    assert len(seen) == 10  # one page request per link, all failed
    assert len(clock.sleeps) == len(seen) - 1 and all(gap >= SPACING_SECONDS - 1e-9 for gap in clock.sleeps)


def test_a_503_stops_the_run_at_once_the_rest_are_paused_and_nothing_more_is_requested():
    clock = Clock()
    resolver, seen = resolver_on(lambda request: httpx.Response(503, text="busy"), clock)
    results = resolver.resolve([link(n) for n in range(25)])
    assert len(seen) == 1 and resolver.stop.stopped and resolver.stop.seen == "http_503"
    assert results[0].code == PAUSED and [r.code for r in results].count(PAUSED) == 25  # nothing was resolved, all wait
    assert (
        resolver.resolve([link(99)])[0].code == PAUSED and len(seen) == 1
    )  # and a later call in the same run asks nothing


def test_a_429_stops_the_run():
    clock = Clock()
    resolver, seen = resolver_on(lambda request: httpx.Response(429, text="slow down"), clock)
    resolver.resolve([link(n) for n in range(15)])
    assert len(seen) == 1 and resolver.stop.seen == "http_429"


def sorry_redirect(request):
    return httpx.Response(302, headers={"location": "https://news.google.com/sorry/index?continue=x"})


def test_a_redirect_to_the_sorry_page_stops_the_run():
    clock = Clock()
    resolver, seen = resolver_on(sorry_redirect, clock)
    results = resolver.resolve([link(n) for n in range(12)])
    assert len(seen) == 1 and resolver.stop.seen == "sorry_page" and {r.code for r in results} == {PAUSED}


def test_a_new_run_starts_fresh_the_stop_is_not_remembered_across_resolvers():
    clock = Clock()
    first, _ = resolver_on(lambda request: httpx.Response(429), clock)
    first.resolve([link(1)])
    second, seen = resolver_on(lambda request: httpx.Response(404), clock)
    assert second.resolve([link(1)])[0].code == DECODE_FAILED and len(seen) >= 1


def test_the_hooks_refuse_a_request_off_the_allowed_domain_even_through_the_real_library():
    clock = Clock()
    resolver, seen = resolver_on(
        lambda request: httpx.Response(302, headers={"location": "https://evil.example/x"}), clock
    )
    results = resolver.resolve([link(1)])
    assert [r.code for r in results] == [DECODE_FAILED] and all("evil.example" not in url for url in seen)


def test_links_off_the_domain_are_refused_without_any_request():
    clock = Clock()
    resolver, seen = resolver_on(lambda request: httpx.Response(200, text="x"), clock)
    assert resolver.resolve(["https://evil.example/rss/articles/CBMiabc"])[0].code == REFUSED_LINK and seen == []


# ---- the two small parts on their own ------------------------------------------------------------------------------


def test_the_pacer_never_waits_for_the_first_request_and_never_goes_below_its_floor():
    clock = Clock()
    pacer = RequestPacer(spacing=0.1, clock=clock.time, sleep=clock.sleep)  # asked for less than the floor
    assert pacer.spacing == SPACING_SECONDS
    pacer.wait()
    assert clock.sleeps == []
    pacer.wait()
    assert clock.sleeps == [SPACING_SECONDS] and pacer.requests == 2
    clock.now += 10
    pacer.wait()
    assert len(clock.sleeps) == 1  # enough time had already passed: no extra wait


PUSHBACKS = [
    (429, "", "/a", True), (503, "", "/a", True), (200, "", "/a", False), (404, "", "/a", False),
    (500, "", "/a", False), (302, "https://news.google.com/sorry/x", "/a", True), (200, "", "/sorry/index", True),
    (302, "https://pub.example/a", "/a", False),
]  # fmt: skip


@pytest.mark.parametrize(("status", "location", "path", "stopped"), PUSHBACKS)
def test_what_counts_as_a_pushback(status, location, path, stopped):
    stop = PushbackStop()
    response = httpx.Response(
        status,
        headers={"location": location} if location else {},
        request=httpx.Request("GET", f"https://news.google.com{path}"),
    )
    stop.observe(response)
    assert stop.stopped is stopped
