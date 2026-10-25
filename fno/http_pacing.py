"""Polite HTTP for free public sources (NSE website and archives): space requests per host, back off when refused.

Every session in the process shares one pacer, so all commands and downloads together never send a host more than
one request per spacing interval. A "too many requests" or "forbidden" answer pauses that
host for a cool-off period instead of retrying into a longer block.
"""

from __future__ import annotations

import threading
import time
from urllib.parse import urlparse

import requests

DEFAULT_SPACING_SECONDS = 1.0
HOST_SPACING_SECONDS = {
    "www.nseindia.com": 1.0,
    "nsearchives.nseindia.com": 1.0,
}
REFUSAL_STATUS_CODES = (403, 429)
REFUSALS_BEFORE_PAUSE = 2  # NSE can refuse once until its cookies are set; two in a row means we are blocked
COOL_OFF_SECONDS = 15 * 60
COOLING_OFF_MESSAGE = "{host} refused requests (HTTP {status}); not calling it for {minutes} minutes"


class SourceCoolingOff(requests.RequestException):
    """The host refused us recently; no request is sent until the cool-off ends."""


class RequestPacer:
    def __init__(self, spacing: dict[str, float] | None = None, cool_off_seconds: float = COOL_OFF_SECONDS, clock=None):
        self.spacing = HOST_SPACING_SECONDS if spacing is None else spacing
        self.cool_off_seconds = cool_off_seconds
        self.clock = clock or time.monotonic
        self.sleep = time.sleep
        self._next_allowed: dict[str, float] = {}
        self._paused: dict[str, tuple[float, str]] = {}
        self._refusals: dict[str, int] = {}
        self._lock = threading.Lock()

    def wait_turn(self, host: str) -> None:
        """Block until the host may be called again; raise if it is cooling off after a refusal."""
        with self._lock:
            paused = self._paused.get(host)
            if paused and self.clock() < paused[0]:
                raise SourceCoolingOff(paused[1])
            now = self.clock()
            start = max(now, self._next_allowed.get(host, now))
            self._next_allowed[host] = start + self.spacing.get(host, DEFAULT_SPACING_SECONDS)
        if start > now:
            self.sleep(start - now)

    def observe(self, host: str, status: int) -> None:
        with self._lock:
            if status not in REFUSAL_STATUS_CODES:
                self._refusals[host] = 0
                return
            self._refusals[host] = self._refusals.get(host, 0) + 1
            if self._refusals[host] >= REFUSALS_BEFORE_PAUSE:
                minutes = round(self.cool_off_seconds / 60)
                message = COOLING_OFF_MESSAGE.format(host=host, status=status, minutes=minutes)
                self._paused[host] = (self.clock() + self.cool_off_seconds, message)
                self._refusals[host] = 0


SHARED_PACER = RequestPacer()


class PacedSession(requests.Session):
    """A requests.Session that waits its turn per host and stops calling a host that refused it."""

    def __init__(self, pacer: RequestPacer | None = None):
        super().__init__()
        self.pacer = pacer or SHARED_PACER

    def request(self, method, url, *args, **kwargs):
        host = urlparse(url).hostname or ""
        self.pacer.wait_turn(host)
        response = super().request(method, url, *args, **kwargs)
        self.pacer.observe(host, response.status_code)
        return response
