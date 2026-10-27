"""The page fetcher's vocabulary (NP4a): one fixed code per request, never a URL, a host or a page's text."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

OK = "ok"
URL_REFUSED = "url_refused"  # not https, or it carries credentials or a port, or the host is not a plain name
HOST_NOT_ALLOWED = (
    "host_not_allowed"  # not a listed outlet, or an outlet (or a parent of it) that refuses automated reads
)
BLOCKED_ADDRESS = "blocked_address"  # the name resolves to an address that is not global (private, CGNAT, NAT64 ...)
REDIRECT_REFUSED = (
    "redirect_refused"  # a hop left the allowlist, or there were too many hops, or the redirect was malformed
)
TOO_LARGE = "too_large"  # over the byte cap once decoded: nothing is kept
NOT_HTML = "not_html"
ROBOTS_DISALLOWED = "robots_disallowed"
ROBOTS_UNREADABLE = "robots_unreadable"  # robots.txt could not be read this run: the host's pages are not read
HOST_STOPPED = "host_stopped"  # the host refused or pushed back earlier in this run
REFUSED = "refused"  # 401, 403, 429 or 503: the host is stopped for the run and not retried
HTTP_ERROR = "http_error"
ERROR = "error"  # a network error or timeout (no message is kept)
CODES = (OK, URL_REFUSED, HOST_NOT_ALLOWED, BLOCKED_ADDRESS, REDIRECT_REFUSED, TOO_LARGE, NOT_HTML, ROBOTS_DISALLOWED,
         ROBOTS_UNREADABLE, HOST_STOPPED, REFUSED, HTTP_ERROR, ERROR)  # fmt: skip


@dataclass(frozen=True)
class Page:
    code: str
    final_url: str = field(default="", repr=False)  # private: never printed, even by a traceback
    content_type: str = ""
    status: int = 0  # the HTTP status of an `http_error`, for the robots.txt rules
    body: bytes = field(default=b"", repr=False)


class PageFetcher(ABC):
    @abstractmethod
    def fetch(self, url: str) -> Page:
        """One page, or a code saying why not. Never raises for a network or protocol problem."""
