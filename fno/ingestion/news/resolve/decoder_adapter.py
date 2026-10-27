"""The `googlenewsdecoder` adapter of the link resolver (NP2b). The library drives an UNOFFICIAL endpoint of the news
service (one page request per link, then one POST per batch), so it can stop working without notice; that is why it sits
behind `LinkResolver` and why a failure is a fixed code, never a crash. Rules, all tested with a fake library:

- a link is requested only when it is https on the allowed domain (`EgressGuard`); otherwise `refused_link`, no request;
- every request the library makes, redirects included, passes a request hook that refuses any host off the allowed
  domains and any scheme but https (the library follows redirects itself, so a hook sees every hop);
- at most ten links per batch (the library's batch is one POST), at least `interval_seconds` between page requests;
- a library message is never kept (it can quote the link); each link gets one fixed code;
- a result is kept only through `accept` (a clean https link that is not the service's own)."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from fno.ingestion.news.article.source_facts import clean_https_link
from fno.ingestion.news.resolve.accept import accept
from fno.ingestion.news.resolve.guard import EgressGuard
from fno.ingestion.news.resolve.model import DECODE_FAILED, ERROR, REFUSED_LINK, LinkResolver, Resolved
from fno.shared.constants import RESEARCH_USER_AGENT

BATCH = 10
MIN_INTERVAL_SECONDS = 2  # the library takes whole seconds; the plan's floor is 1.5
TIMEOUT_SECONDS = 20.0


def egress_hook(guard: EgressGuard) -> Callable:
    """An httpx request hook: raises for any request that is not https to an allowed domain."""

    def refuse_off_domain(request) -> None:
        import httpx

        if request.url.scheme != "https" or not guard.allows_host(request.url.host):
            raise httpx.RequestError("request refused: not https to the allowed domain", request=request)

    return refuse_off_domain


def library_decoder(timeout: float, user_agent: str):
    """A `googlenewsdecoder.GoogleDecoder` (imported here, so nothing else needs the library)."""
    from googlenewsdecoder import GoogleDecoder

    return GoogleDecoder(timeout=timeout, user_agent=user_agent)


class GoogleNewsDecoderResolver(LinkResolver):
    def __init__(
        self,
        guard: EgressGuard,
        interval_seconds: int = MIN_INTERVAL_SECONDS,
        timeout: float = TIMEOUT_SECONDS,
        user_agent: str = RESEARCH_USER_AGENT,
        decoder_factory=library_decoder,
    ):
        self.guard = guard
        self.interval = max(int(interval_seconds), MIN_INTERVAL_SECONDS)
        self.timeout, self.user_agent, self.decoder_factory = timeout, user_agent, decoder_factory

    def resolve(self, links: Sequence[str]) -> list[Resolved]:
        results = [Resolved(REFUSED_LINK) for _ in links]
        allowed = [i for i, link in enumerate(links) if self.guard.allows_link(link)]
        links = [clean_https_link(link) for link in links]  # send exactly what was checked ("" for a refused one)
        for start in range(0, len(allowed), BATCH):
            chunk = allowed[start : start + BATCH]
            for index, outcome in zip(chunk, self._batch([links[i] for i in chunk]), strict=True):
                results[index] = outcome
        return results

    def _batch(self, links: list[str]) -> list[Resolved]:
        try:
            with self.decoder_factory(self.timeout, self.user_agent) as decoder:
                decoder.client.event_hooks = {"request": [egress_hook(self.guard)], "response": []}
                answers = decoder.decode_google_news_urls(links, interval=self.interval)
            if len(answers) != len(links):
                return [Resolved(ERROR) for _ in links]
            return [self._one(answer) for answer in answers]
        except Exception:  # noqa: BLE001 - a fixed code per link; the caller counts codes and alerts on a high error share
            return [Resolved(ERROR) for _ in links]

    def _one(self, answer: object) -> Resolved:
        if not isinstance(answer, dict) or not answer.get("success"):
            return Resolved(DECODE_FAILED)
        return accept(answer.get("decoded_url"), self.guard)
