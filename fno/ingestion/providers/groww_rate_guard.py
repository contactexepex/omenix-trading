"""Groww's rate-limit answer named, and the process stopped for a minute after it (story GW1, parts 3 and 4).

Groww sends its rate limit as `status: FAILURE` with code `429`, which SDK 1.5 raises as a plain `GrowwAPIException`
(A16, 16 Oct), or as HTTP 429 (`GrowwAPIRateLimitException`). A4's public sidecars keep an error's class name only, so
the first form hid every 429. Here both arrive as `GrowwRateLimited`. After one, every read call of this process fails
at once for `PAUSE_SECONDS` (Groww's per-minute window) instead of spending the budget another taker needs: an A4
attempt then ends at its first 429, and its own retry gap follows."""

from __future__ import annotations

import time
from collections.abc import Callable

from fno.ingestion.providers.groww_quiet_windows import NoQuietWindows, QuietWindows

RATE_LIMIT_CODE = "429"
PAUSE_SECONDS = 60
LIMITED = "Groww answered 429 (rate limit)"
PAUSED = "Groww calls paused for {left:.0f} s after a 429 (rate limit); nothing was sent"


class GrowwRateLimited(RuntimeError):
    """Groww refused a call for its rate limit; the code is kept, never Groww's message."""

    code = RATE_LIMIT_CODE


class GrowwRateLimitPaused(RuntimeError):
    """A call came within the pause after a 429; nothing reached Groww."""


def is_rate_limit(exc: Exception) -> bool:
    return str(getattr(exc, "code", "") or "") == RATE_LIMIT_CODE


class RateLimitPause:
    def __init__(self, seconds: float = PAUSE_SECONDS, clock: Callable[[], float] = time.monotonic):
        self.seconds, self.clock = seconds, clock
        self._until = float("-inf")

    def check(self) -> None:
        left = self._until - self.clock()
        if left > 0:
            raise GrowwRateLimitPaused(PAUSED.format(left=left))

    def start(self) -> None:
        self._until = self.clock() + self.seconds


class RateGuardedGroww:
    """Every callable the client gives is refused unsent inside A16's quiet windows (when its provider has them), then
    goes through the pause and the 429 translation; constants pass as they are."""

    __slots__ = ("_client", "_pause", "_quiet")

    def __init__(self, client: Callable[[], object], pause: RateLimitPause, quiet: QuietWindows | None = None):
        self._client, self._pause = client, pause  # called on each use: the sign-in decides the client
        self._quiet = quiet or NoQuietWindows()

    def __getattr__(self, name: str):
        value = getattr(self._client(), name)
        return self._guarded(value) if callable(value) else value

    def _guarded(self, call):
        def guarded(*args, **kwargs):
            self._quiet.check()
            self._pause.check()
            try:
                return call(*args, **kwargs)
            except Exception as exc:
                if not is_rate_limit(exc):
                    raise
                self._pause.start()
                raise GrowwRateLimited(LIMITED) from None  # Groww's own text is never carried on

        return guarded
