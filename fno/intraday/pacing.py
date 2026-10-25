"""Keeps parallel requests under the source's rate limit (story A16 step 0: Groww answered 5 a second with 4 workers
without errors, began failing near 10 a second): request starts are spaced at least `interval` seconds apart."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable


class RatePacer:
    def __init__(self, per_second: float, clock: Callable[[], float] = time.monotonic, sleep=time.sleep):
        self.interval, self.clock, self.sleep = 1 / per_second, clock, sleep
        self._lock, self._next = threading.Lock(), 0.0

    def wait(self) -> None:
        with self._lock:
            now = self.clock()
            start = max(now, self._next)
            self._next = start + self.interval
        if start > now:
            self.sleep(start - now)
