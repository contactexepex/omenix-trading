"""The rate limit (story R1): one strategy for every host and every daily budget. Minimum spacing between calls, a
per-minute budget and a per-day budget; a call waits for its turn, or is deferred when the wait would pass `max_wait`.

Values (not code) differ by source: NSE 1 request a second; Groww 10 a second, 300 a minute, 150 sign-ins a day; polite
defaults for new sources. The per-day budget is counted through a ledger so it can outlive a process (the global-cues
attempt log is such a ledger); spacing and the per-minute window live in the process, since they cannot outlive a
minute."""

from __future__ import annotations

import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from fno.shared.resilience.outcomes import Deferred

MINUTE_SECONDS = 60.0


class DayLedger(Protocol):
    def used_today(self) -> int: ...

    def record(self) -> None: ...


class MemoryLedger:
    """A per-run ledger: its count dies with the process (the code that uses it says the budget is per run)."""

    def __init__(self) -> None:
        self.count = 0

    def used_today(self) -> int:
        return self.count

    def record(self) -> None:
        self.count += 1


@dataclass(frozen=True)
class RateSettings:
    min_spacing_seconds: float = 1.0
    per_minute: int | None = None
    per_day: int | None = None
    max_wait_seconds: float = 120.0  # a wait longer than this is a deferral, not a sleep


class RateLimit:
    def __init__(self, source: str, settings: RateSettings, ledger: DayLedger | None = None,
                 sleep: Callable[[float], None] = time.sleep, clock: Callable[[], float] = time.monotonic):  # fmt: skip
        self.source, self.settings, self.ledger = source, settings, ledger or MemoryLedger()
        self.sleep, self.clock = sleep, clock
        self._last: float | None = None
        self._recent: deque[float] = deque()

    def acquire(self) -> None:
        """Waits for this call's turn and counts it; raises Deferred (nothing counted) when the day's budget is spent or
        the wait would exceed `max_wait_seconds`."""
        s = self.settings
        if s.per_day is not None and self.ledger.used_today() >= s.per_day:
            raise Deferred(self.source, f"daily budget of {s.per_day} calls is spent")
        wait = self._wait_needed()
        if wait > s.max_wait_seconds:
            raise Deferred(self.source, f"rate limit: would have to wait {wait:.0f} s")
        if wait > 0:
            self.sleep(wait)
        now = self.clock()
        self._last = now
        self._recent.append(now)
        self.ledger.record()

    def _wait_needed(self) -> float:
        s, now = self.settings, self.clock()
        while self._recent and now - self._recent[0] >= MINUTE_SECONDS:
            self._recent.popleft()
        wait = 0.0
        if self._last is not None:
            wait = max(wait, self._last + s.min_spacing_seconds - now)
        if s.per_minute is not None and len(self._recent) >= s.per_minute:
            wait = max(wait, self._recent[0] + MINUTE_SECONDS - now)
        return wait
