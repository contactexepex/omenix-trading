"""robots.txt (NP4a; owner default: honoured). Read once per host per run through the SAME fetcher, guards, spacer and
host stop as a page, never around them. Rules (RFC 9309): a file that is absent (404, 410) or another client error means
no restriction; a server error, a network failure, a redirect to another host or a body over the cap means the host's
pages are not read this run; a refusal (401, 403, 429, 503) stops the host like any other request."""

from __future__ import annotations

from collections.abc import Callable
from urllib.robotparser import RobotFileParser

from fno.ingestion.news.pages import model

AGENT = "fno-desk"  # the product token in our User-Agent
ROBOTS_BYTES = 500_000
ALLOW_ALL = "allow_all"
UNREADABLE = "unreadable"

Getter = Callable[[str], "tuple[int, bytes | None]"]  # url -> (status, body) ; status 0 = failed


class RobotsCache:
    def __init__(self, get: Getter):
        """`get`: fetches a robots.txt URL through the fetcher's guards; (status, body), status 0 when it failed."""
        self.get = get
        self.hosts: dict[str, RobotFileParser | str] = {}

    def verdict(self, host: str, url: str) -> str:
        """`ok`, `robots_disallowed` or `robots_unreadable` for this page URL."""
        rules = self.hosts.get(host)
        if rules is None:
            rules = self.hosts[host] = self._read(host)
        if rules == UNREADABLE:
            return model.ROBOTS_UNREADABLE
        if rules == ALLOW_ALL or rules.can_fetch(AGENT, url):
            return model.OK
        return model.ROBOTS_DISALLOWED

    def _read(self, host: str) -> RobotFileParser | str:
        status, body = self.get(f"https://{host}/robots.txt")
        if status in (404, 410) or 400 <= status < 500:
            return ALLOW_ALL
        if status != 200 or body is None:
            return UNREADABLE
        parser = RobotFileParser()
        parser.parse(body.decode("utf-8", errors="replace").splitlines())
        return parser
