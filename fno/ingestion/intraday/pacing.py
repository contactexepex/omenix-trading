"""Keeps parallel requests under the source's rate limit (story A16 step 0: Groww answered 5 a second with 4 workers
without errors, began failing near 10 a second): request starts are spaced at least `interval` seconds apart. Since
story R1d1 the spacing is the shared `RateLimit` (thread-safe, first start free, no cap on a wait), per caller."""

from __future__ import annotations

import time
from collections.abc import Callable

from fno.shared.resilience.rate_limit import RateLimit, RateSettings

SOURCE = "groww"


class RatePacer:
    def __init__(self, per_second: float, clock: Callable[[], float] = time.monotonic, sleep=time.sleep):
        self.interval = 1 / per_second
        # a caller's own spacing, never a host ceiling; no deferral: a worker waits its turn as it always has
        settings = RateSettings(min_spacing_seconds=self.interval, max_wait_seconds=float("inf"))
        self._limit = RateLimit(SOURCE, settings, sleep=sleep, clock=clock)

    def wait(self) -> None:
        self._limit.acquire()
