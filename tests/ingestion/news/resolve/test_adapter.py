"""NP2b: the decoder adapter against a fake library (no network): codes, batching, order, egress hook, interval."""

from __future__ import annotations

import httpx
import pytest

from fno.ingestion.news.resolve.decoder_adapter import (
    BATCH,
    MIN_INTERVAL_SECONDS,
    GoogleNewsDecoderResolver,
    egress_hook,
)
from fno.ingestion.news.resolve.guard import EgressGuard
from fno.ingestion.news.resolve.model import BAD_RESULT, DECODE_FAILED, ERROR, REFUSED_LINK, RESOLVED, LinkResolver

GUARD = EgressGuard(["svc.example"])
LINK = "https://news.svc.example/rss/articles/{n}?oc=5"


class FakeClient:
    event_hooks: dict = {}


class FakeDecoder:
    """Records its calls; `answer(link)` decides each result."""

    instances: list = []

    def __init__(self, answer):
        self.answer, self.calls, self.client = answer, [], FakeClient()
        FakeDecoder.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def decode_google_news_urls(self, links, interval=None):
        self.calls.append((list(links), interval))
        return [self.answer(link) for link in links]


def resolver(answer, **kwargs) -> GoogleNewsDecoderResolver:
    FakeDecoder.instances = []
    return GoogleNewsDecoderResolver(GUARD, decoder_factory=lambda timeout, agent: FakeDecoder(answer), **kwargs)


def ok(link):
    return {"success": True, "decoded_url": "https://pub.example/" + link.rsplit("/", 1)[-1].split("?")[0]}


def test_the_adapter_is_a_link_resolver():
    assert isinstance(resolver(ok), LinkResolver)


def test_each_link_gets_its_result_in_order_and_a_refused_link_is_never_sent():
    links = [LINK.format(n=1), "https://evil.example/x", LINK.format(n=2), "http://news.svc.example/a"]
    results = resolver(ok).resolve(links)
    assert [r.code for r in results] == [RESOLVED, REFUSED_LINK, RESOLVED, REFUSED_LINK]
    assert [r.url for r in results] == ["https://pub.example/1", "", "https://pub.example/2", ""]
    assert FakeDecoder.instances[0].calls[0][0] == [LINK.format(n=1), LINK.format(n=2)]


def test_nothing_refused_means_no_decoder_is_even_created():
    assert [r.code for r in resolver(ok).resolve(["https://evil.example/x"])] == [
        REFUSED_LINK
    ] and FakeDecoder.instances == []
    assert resolver(ok).resolve([]) == []


def test_links_go_in_batches_of_ten_in_order():
    links = [LINK.format(n=n) for n in range(25)]
    results = resolver(ok).resolve(links)
    assert [len(d.calls[0][0]) for d in FakeDecoder.instances] == [10, 10, 5] and BATCH == 10
    assert [r.url for r in results] == [f"https://pub.example/{n}" for n in range(25)]


def test_the_wait_between_page_requests_is_never_below_the_floor():
    resolver(ok, interval_seconds=0).resolve([LINK.format(n=1)])
    resolver(ok, interval_seconds=1).resolve([LINK.format(n=1)])
    assert FakeDecoder.instances[0].calls[0][1] == MIN_INTERVAL_SECONDS and MIN_INTERVAL_SECONDS >= 2
    assert resolver(ok, interval_seconds=5).interval == 5


def test_a_failure_the_library_reports_is_a_fixed_code_and_its_message_is_never_kept():
    link = LINK.format(n=1)
    results = resolver(lambda l: {"success": False, "message": f"Request error: could not fetch {l}"}).resolve([link])
    assert results == [type(results[0])(DECODE_FAILED)] and link not in repr(results)


@pytest.mark.parametrize("answer", ["text", None, 5, [], {"success": True}, {"success": True, "decoded_url": 5}])
def test_an_answer_that_is_not_a_proper_result_is_a_fixed_code(answer):
    code = resolver(lambda l: answer).resolve([LINK.format(n=1)])[0].code
    assert code in (DECODE_FAILED, BAD_RESULT)


def test_a_url_back_on_the_service_or_not_clean_is_a_bad_result():
    cases = {1: "https://news.svc.example/read/x", 2: "http://pub.example/a", 3: "https://pub.example/a b"}
    results = resolver(lambda l: {"success": True, "decoded_url": cases[int(l.split("/")[-1].split("?")[0])]}).resolve(
        [LINK.format(n=n) for n in cases]
    )
    assert [r.code for r in results] == [BAD_RESULT] * 3


def test_a_library_that_raises_costs_only_its_batch_and_never_the_run():
    calls = []

    def answer(link):
        calls.append(link)
        if len(calls) == 3:
            raise RuntimeError(f"boom {link}")
        return ok(link)

    results = resolver(answer).resolve([LINK.format(n=n) for n in range(12)])
    assert [r.code for r in results[:10]] == [ERROR] * 10 and [r.code for r in results[10:]] == [RESOLVED] * 2
    assert "boom" not in repr(results)


def test_an_answer_list_of_the_wrong_length_is_an_error_for_the_whole_batch():
    class Short(FakeDecoder):
        def decode_google_news_urls(self, links, interval=None):
            return [ok(links[0])]

    FakeDecoder.instances = []
    resolver_ = GoogleNewsDecoderResolver(GUARD, decoder_factory=lambda t, a: Short(ok))
    assert [r.code for r in resolver_.resolve([LINK.format(n=1), LINK.format(n=2)])] == [ERROR, ERROR]


def test_the_egress_hook_is_installed_on_every_decoder_client():
    resolver(ok).resolve([LINK.format(n=1)])
    hooks = FakeDecoder.instances[0].client.event_hooks
    assert len(hooks["request"]) == 1 and hooks["response"] == []


# ---- the hook on a REAL httpx client (a mock transport: nothing leaves the machine) ------------------------------


def client_with_hook() -> tuple[httpx.Client, list]:
    seen: list = []

    def handler(request):
        seen.append(str(request.url))
        return httpx.Response(200, text="ok")

    client = httpx.Client(transport=httpx.MockTransport(handler), event_hooks={"request": [egress_hook(GUARD)]})
    return client, seen


def test_the_hook_lets_an_https_request_to_the_allowed_domain_through():
    client, seen = client_with_hook()
    assert client.get("https://news.svc.example/rss/articles/a").status_code == 200 and len(seen) == 1


@pytest.mark.parametrize(
    "url",
    [
        "http://news.svc.example/a",
        "https://evil.example/a",
        "https://svc.example.evil.example/a",
        "https://user@evil.example/",
    ],
)
def test_the_hook_refuses_everything_else_before_it_is_sent(url):
    client, seen = client_with_hook()
    with pytest.raises(httpx.RequestError):
        client.get(url)
    assert seen == []


def test_a_redirect_to_another_host_is_refused_at_the_hop_by_the_same_hook():
    seen: list = []

    def handler(request):
        seen.append(str(request.url))
        if request.url.host == "news.svc.example":
            return httpx.Response(302, headers={"location": "https://evil.example/landing"})
        return httpx.Response(200, text="ok")

    client = httpx.Client(
        transport=httpx.MockTransport(handler), event_hooks={"request": [egress_hook(GUARD)]}, follow_redirects=True
    )
    with pytest.raises(httpx.RequestError):
        client.get("https://news.svc.example/rss/articles/a")
    assert seen == ["https://news.svc.example/rss/articles/a"]  # the second hop never reached the transport
