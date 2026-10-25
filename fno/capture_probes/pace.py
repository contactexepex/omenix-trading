"""The study pace (story MS-P0b section 3): one request at a time, each start at least the source's gap after the
last one. One pace per source; the two sources never run at once, so no lock is needed."""

from __future__ import annotations

import time
from collections.abc import Callable


class StudyPace:
    def __init__(self, gap_seconds: float, clock: Callable[[], float] = time.monotonic, sleep=time.sleep):
        self.gap, self.clock, self.sleep = gap_seconds, clock, sleep
        self._last_start: float | None = None

    def wait_turn(self) -> None:
        """Blocks until the gap since the last start has passed, then counts this moment as the new start."""
        now = self.clock()
        if self._last_start is not None and now < self._last_start + self.gap:
            self.sleep(self._last_start + self.gap - now)
            now = self._last_start + self.gap
        self._last_start = now
