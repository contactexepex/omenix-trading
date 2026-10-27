"""The page fetcher (NP4a; NP0 section 2d): `HttpsPageFetcher`, a `PageFetcher` over `requests`. Every request AND every
redirect hop (followed by hand, at most `MAX_HOPS`) must pass, in order:

1. the URL is https, with no credentials and no port, and a plain host name; 2. the host is a listed outlet that
allows automated reads, with no listed parent that refuses them (`may_fetch`); 3. the host has not refused or pushed
back earlier in this run (a 401, 403, 429 or 503 stops that host, not the others); 4. every address the name resolves
to is global (`pages/address.py`; checked BEFORE robots.txt, so nothing is requested from a name that resolves
inside a network); 5. robots.txt allows the path (read through this same method, once per host per run).

Then at least `spacing` seconds since ANY earlier page request (across hosts; NP2b's `RequestSpacer`, reused), a GET
with one polite User-Agent, no cookies kept, TLS verification on, a timeout, and the body streamed up to `MAX_BYTES`
of DECODED bytes (a small gzip bomb is `too_large`; nothing is kept). Only html or xhtml is accepted. Nothing here
raises for a network or protocol problem and no code carries a URL, a host or a message.

Known gap, stated: the address is checked, then the library connects, so a name could change its answer in between.
The names are the public listed outlets and only GET is sent; pinning the connection to the checked address is not
built."""

from __future__ import annotations

from collections.abc import Callable
from urllib.parse import urljoin, urlsplit

import requests

from fno.ingestion.news.pages import model
from fno.ingestion.news.pages.address import Resolver, all_global, system_resolver
from fno.ingestion.news.pages.model import Page, PageFetcher
from fno.ingestion.news.pages.robots import ROBOTS_BYTES, RobotsCache
from fno.ingestion.news.resolve.pacing import RequestSpacer
from fno.ingestion.news.session import RejectAllCookies
from fno.ingestion.news.sources.rules import SourceRules, plain_host
from fno.shared.constants import RESEARCH_USER_AGENT

MAX_BYTES = 4_000_000
TIMEOUT_SECONDS = 20.0
MAX_HOPS = 5
STOP_STATUSES = (401, 403, 429, 503)
HTML_TYPES = ("text/html", "application/xhtml+xml")
CHUNK = 65_536


class HttpsPageFetcher(PageFetcher):
    def __init__(
        self,
        rules: SourceRules,
        spacer: RequestSpacer | None = None,
        session: requests.Session | None = None,
        resolver: Resolver = system_resolver,
        host_allowed: Callable[[str], bool] | None = None,
        max_bytes: int = MAX_BYTES,
    ):
        """`host_allowed`: the allowlist test, `rules.may_fetch` unless the outlet probe looks at refusing outlets."""
        self.rules, self.spacer, self.resolver, self.max_bytes = rules, spacer or RequestSpacer(), resolver, max_bytes
        self.host_allowed = host_allowed or rules.may_fetch
        self.session = session or requests.Session()
        self.session.headers["User-Agent"] = RESEARCH_USER_AGENT
        self.session.cookies.set_policy(RejectAllCookies())
        self.stopped: set[str] = set()
        self.robots = RobotsCache(self._robots_status)

    def fetch(self, url: str) -> Page:
        return self._follow(url, check_robots=True, limit=self.max_bytes, accept=HTML_TYPES)

    # ---- one URL, with hops by hand ------------------------------------------------------------------------------
    def _follow(self, url: str, check_robots: bool, limit: int, accept: tuple[str, ...]) -> Page:
        first_host = ""
        for hop in range(MAX_HOPS + 1):
            host, refusal = self._admit(url, check_robots)
            if refusal:
                moved = hop > 0 and refusal in (model.URL_REFUSED, model.HOST_NOT_ALLOWED, model.BLOCKED_ADDRESS)
                return Page(
                    model.REDIRECT_REFUSED if moved else refusal, url
                )  # a hop that leaves the rules is a refused redirect
            if not first_host:
                first_host = host
            elif not check_robots and host != first_host:
                return Page(model.REDIRECT_REFUSED, url)  # robots.txt may not hop to another host
            response = self._get(url)
            if isinstance(response, str):
                return Page(response, url)
            with response:
                if response.status_code in STOP_STATUSES:
                    self.stopped.add(host)
                    return Page(model.REFUSED, url)
                if 300 <= response.status_code < 400:
                    url = self._next(url, response)
                    if not url:
                        return Page(model.REDIRECT_REFUSED, "")
                    continue
                if response.status_code >= 400:
                    return Page(model.HTTP_ERROR, url, status=response.status_code)
                return self._body(response, url, limit, accept)
        return Page(model.REDIRECT_REFUSED, url)

    def _admit(self, url: str, check_robots: bool) -> tuple[str, str]:
        """(host, "") when the request may go out, else ("", the code)."""
        try:
            parts = urlsplit(url)
            host = plain_host(parts.hostname)
            clean = parts.scheme == "https" and parts.username is None and parts.password is None and parts.port is None
        except ValueError:
            return "", model.URL_REFUSED
        if not clean or not host:
            return "", model.URL_REFUSED
        if not self.host_allowed(host):
            return "", model.HOST_NOT_ALLOWED
        if host in self.stopped:
            return "", model.HOST_STOPPED
        if not all_global(host, self.resolver):
            return "", model.BLOCKED_ADDRESS
        if check_robots:
            verdict = self.robots.verdict(host, url)
            if verdict != model.OK:
                return "", verdict
            if host in self.stopped:  # reading robots.txt got the host stopped
                return "", model.HOST_STOPPED
        return host, ""

    def _get(self, url: str):
        self.spacer.wait()
        try:
            return self.session.get(url, timeout=TIMEOUT_SECONDS, allow_redirects=False, stream=True)
        except requests.RequestException:
            return model.ERROR

    def _next(self, url: str, response) -> str:
        location = response.headers.get("location") or ""
        return urljoin(url, location) if location and len(location) < 2000 else ""

    def _body(self, response, url: str, limit: int, accept: tuple[str, ...]) -> Page:
        kind = (response.headers.get("content-type") or "").split(";")[0].strip().lower()
        if kind not in accept:
            return Page(model.NOT_HTML, url)
        chunks, size = [], 0
        try:
            for chunk in response.iter_content(CHUNK):  # decoded bytes: a gzip bomb stops at the cap
                size += len(chunk)
                if size > limit:
                    return Page(model.TOO_LARGE, url)
                chunks.append(chunk)
        except requests.RequestException:
            return Page(model.ERROR, url)
        return Page(model.OK, url, kind, body=b"".join(chunks))

    # ---- robots.txt through the same guards ------------------------------------------------------------------------
    def _robots_status(self, url: str) -> tuple[int, bytes | None]:
        page = self._follow(url, check_robots=False, limit=ROBOTS_BYTES, accept=("text/plain", "text/html", ""))
        if page.code == model.OK:
            return 200, page.body
        if page.code == model.HTTP_ERROR:
            return page.status, None
        return 0, None  # refused, stopped, redirected away, too large, a network error: unreadable
