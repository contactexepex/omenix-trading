"""Our own pacing and our own stop for the link resolver (NP2b, round 2). The library paces only AFTER a successful page
request (it `continue`s past its wait when a request fails), and never stops on a refusal: against a service that is
refusing us it would send about thirty requests a batch with no pause, batch after batch (reproduced by two judges on
the real library). So both live here, in the request and response hooks of its one HTTP client, where every request
and every redirect hop passes:

- `RequestSpacer`: at least `spacing` seconds between ANY two requests, a failed one included;
- `PushbackStop`: the first refusal (HTTP 429 or 503, or a redirect to the service's "sorry" page) stops every later
  request of the run for good, so a service that is pushing back is never asked again until the next run."""

from __future__ import annotations

import time
from collections.abc import Callable

SPACING_SECONDS = 1.5
PUSHBACK_STATUSES = (429, 503)
SORRY_MARKER = "/sorry/"


class RequestSpacer:
    def __init__(self, spacing: float = SPACING_SECONDS, clock: Callable[[], float] = time.monotonic,
                 sleep: Callable[[float], None] = time.sleep):  # fmt: skip
        self.spacing, self.clock, self.sleep = max(spacing, SPACING_SECONDS), clock, sleep
        self.last: float | None = None
        self.requests = 0

    def wait(self) -> None:
        """Block until `spacing` seconds have passed since the previous request, then count this one."""
        if self.last is not None:
            gap = self.spacing - (self.clock() - self.last)
            if gap > 0:
                self.sleep(gap)
        self.last = self.clock()
        self.requests += 1


class PushbackStop:
    def __init__(self) -> None:
        self.stopped = False
        self.seen: str = ""  # the kind of refusal (a fixed word), never a URL

    def observe(self, response) -> None:
        if response.status_code in PUSHBACK_STATUSES:
            self.stopped, self.seen = True, f"http_{response.status_code}"
        elif SORRY_MARKER in (response.headers.get("location") or "") or SORRY_MARKER in response.url.path:
            self.stopped, self.seen = True, "sorry_page"
