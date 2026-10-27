"""A fixed-length pause (story R1d1): after a refusal a source is left alone for a set time, then every caller may go
again at once. This is deliberately not the circuit breaker: no half-open and no single probe, so concurrent readers are
never deferred behind one (Groww's 429 pause works this way today). In process only; no log, no alert."""

from __future__ import annotations

import time
from collections.abc import Callable


class FixedPause:
    def __init__(self, seconds: float, clock: Callable[[], float] = time.monotonic):
        self.seconds, self.clock = seconds, clock
        self._until = float("-inf")

    def remaining(self) -> float:
        """Seconds left in the pause; zero or less when none is running."""
        return self._until - self.clock()

    def start(self) -> None:
        self._until = self.clock() + self.seconds
