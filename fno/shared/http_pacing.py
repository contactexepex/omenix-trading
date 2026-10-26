"""Polite HTTP for free public sources (NSE website and archives): space requests per host, back off when refused.

Every session in the process shares one pacer (`SHARED_PACER`, story R1b: `NsePacer`, built on the shared resilience
layer), so all commands and downloads together never send a host more than one request per spacing interval. A "too
many requests" or "forbidden" answer pauses that host for a cool-off period instead of retrying into a longer block.
"""

from __future__ import annotations

from urllib.parse import urlparse

import requests

from fno.shared.nse_pacer import (  # noqa: F401 - the names callers and tests import from here
    COOLING_OFF_MESSAGE,
    DEFAULT_SPACING_SECONDS,
    HOST_SPACING_SECONDS,
    REFUSAL_STATUS_CODES,
    NsePacer,
    SourceCoolingOff,
)

SHARED_PACER = NsePacer()


class PacedSession(requests.Session):
    """A requests.Session that waits its turn per host and stops calling a host that refused it."""

    def __init__(self, pacer: NsePacer | None = None):
        super().__init__()
        self.pacer = pacer or SHARED_PACER

    def request(self, method, url, *args, **kwargs):
        host = urlparse(url).hostname or ""
        self.pacer.wait_turn(host)
        try:
            response = super().request(method, url, *args, **kwargs)
        except BaseException:  # no answer, or anything else: a probe must not be left waiting
            self.pacer.unanswered(host)
            raise
        self.pacer.observe(host, response.status_code)
        return response
