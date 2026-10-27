"""The `googlenewsdecoder` adapter of the link resolver (NP2b). The library drives an UNOFFICIAL endpoint of the news
service, so it can stop working without notice; that is why it sits behind `LinkResolver` and why a failure is a fixed
code, never a crash. What the library really does, read at the locked version: it takes ONLY the article id out of a
link and requests its own fixed service URLs (a page per link, then one POST per batch); it never requests the link we
hand it. So the real controls are these hooks on its one HTTP client, which sees every request and every redirect hop:

- egress: https only, a host on the allowed domains, no credentials, no explicit port;
- the stop: after the first refusal (HTTP 429/503 or the "sorry" page) nothing more is requested this run
  (`PushbackStop`);
- the pace: at least 1.5 s between ANY two requests, a failed one included (`RequestPacer`; the library's own wait is
  turned off); and, around the library: a link is handed over only when it is clean https on the allowed domain
  (`EgressGuard`), at most ten links go in a batch, a library message is never kept, each link gets one fixed code,
  and a result is kept only through `accept` (a clean https link that is not the service's own)."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from fno.ingestion.news.article.source_facts import clean_https_link
from fno.ingestion.news.resolve.accept import accept
from fno.ingestion.news.resolve.guard import EgressGuard
from fno.ingestion.news.resolve.model import DECODE_FAILED, ERROR, PAUSED, REFUSED_LINK, LinkResolver, Resolved
from fno.ingestion.news.resolve.pacing import PushbackStop, RequestPacer
from fno.shared.constants import RESEARCH_USER_AGENT

BATCH = 10
TIMEOUT_SECONDS = 20.0


def egress_hook(guard: EgressGuard) -> Callable:
    """An httpx request hook: raises for any request that is not https to an allowed domain, without credentials or an
    explicit port."""

    def refuse_off_domain(request) -> None:
        import httpx

        url = request.url
        if url.scheme != "https" or not guard.allows_host(url.host) or url.userinfo or url.port is not None:
            raise httpx.RequestError("request refused: not https to the allowed domain", request=request)

    return refuse_off_domain


def stopped_hook(stop: PushbackStop) -> Callable:
    """An httpx request hook: once the service has pushed back, no request leaves."""

    def refuse_when_stopped(request) -> None:
        import httpx

        if stop.stopped:
            raise httpx.RequestError("request refused: the service pushed back earlier in this run", request=request)

    return refuse_when_stopped


def library_decoder(timeout: float, user_agent: str):
    """A `googlenewsdecoder.GoogleDecoder` (imported here, so nothing else needs the library)."""
    from googlenewsdecoder import GoogleDecoder

    return GoogleDecoder(timeout=timeout, user_agent=user_agent)


class GoogleNewsDecoderResolver(LinkResolver):
    def __init__(self, guard: EgressGuard, pacer: RequestPacer | None = None, timeout: float = TIMEOUT_SECONDS,
                 user_agent: str = RESEARCH_USER_AGENT, decoder_factory=library_decoder):  # fmt: skip
        """One instance is one run: its pacer and its stop live as long as it does."""
        self.guard, self.pacer, self.stop = guard, pacer or RequestPacer(), PushbackStop()
        self.timeout, self.user_agent, self.decoder_factory = timeout, user_agent, decoder_factory

    def resolve(self, links: Sequence[str]) -> list[Resolved]:
        results = [Resolved(REFUSED_LINK) for _ in links]
        allowed = [i for i, link in enumerate(links) if self.guard.allows_link(link)]
        cleaned = [clean_https_link(link) for link in links]
        for start in range(0, len(allowed), BATCH):
            chunk = allowed[start : start + BATCH]
            outcomes = self._batch([cleaned[i] for i in chunk])
            for index, outcome in zip(chunk, outcomes, strict=True):
                results[index] = outcome
        return results

    def _batch(self, links: list[str]) -> list[Resolved]:
        if self.stop.stopped:
            return [Resolved(PAUSED) for _ in links]
        try:
            with self.decoder_factory(self.timeout, self.user_agent) as decoder:
                decoder.client.event_hooks = {
                    "request": [egress_hook(self.guard), stopped_hook(self.stop), lambda request: self.pacer.wait()],
                    "response": [self.stop.observe],
                }
                answers = decoder.decode_google_news_urls(links, interval=None)  # we pace; the library's wait is off
            if len(answers) != len(links):
                return [Resolved(ERROR) for _ in links]
            return [self._after_stop(self._one(answer)) for answer in answers]
        except Exception:  # noqa: BLE001 - a fixed code per link; the caller counts codes and alerts on a high error share
            return [Resolved(ERROR) for _ in links]

    def _after_stop(self, outcome: Resolved) -> Resolved:
        """A link that failed because the service pushed back (not because of the link) waits for the next run."""
        return Resolved(PAUSED) if self.stop.stopped and outcome.code != "resolved" else outcome

    def _one(self, answer: object) -> Resolved:
        if not isinstance(answer, dict) or not answer.get("success"):
            return Resolved(DECODE_FAILED)
        return accept(answer.get("decoded_url"), self.guard)
