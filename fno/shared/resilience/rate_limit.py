"""The rate limit (story R1): one strategy for every host and every daily budget. Minimum spacing between calls, a
per-minute budget and a per-day budget; a call waits for its turn, or is deferred when the wait would pass `max_wait`.

Values (not code) differ by source: NSE 1 request a second; Groww 10 a second, 300 a minute, 150 sign-ins a day; polite
defaults for new sources. The per-day budget is counted through a ledger so it can outlive a process (the global-cues
attempt log is such a ledger); spacing and the per-minute window live in the process, since they cannot outlive a
minute."""

from __future__ import annotations

import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol

from fno.shared.models import IST, now_utc
from fno.shared.resilience.outcomes import Deferred

MINUTE_SECONDS = 60.0


class DayLedger(Protocol):
    def used_today(self) -> int: ...

    def record(self) -> None: ...


class FileDayLedger:
    """A ledger that outlives the process: one UTC time per line in a file; a day is the IST date. Two instances over
    the same file see each other's calls. Each call appends one short line; runs that overlap can at worst miss each
    other's latest line, so the count can read one low (not more) until the next read."""

    def __init__(self, path: Path, clock: Callable[[], datetime] = now_utc) -> None:
        self.path, self.clock = path, clock

    def used_today(self) -> int:
        if not self.path.exists():
            return 0
        today = self.clock().astimezone(IST).date()
        return sum(
            1
            for line in self.path.read_text(encoding="utf-8").splitlines()
            if line.strip() and datetime.fromisoformat(line.strip()).astimezone(IST).date() == today
        )

    def record(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(self.clock().isoformat() + "\n")


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
    """Thread-safe: callers on several threads each reserve a slot under a lock and sleep outside it, so the spacing
    holds across threads (as `RequestPacer` and the intraday `RatePacer` do today)."""

    def __init__(self, source: str, settings: RateSettings, ledger: DayLedger | None = None,
                 sleep: Callable[[float], None] = time.sleep, clock: Callable[[], float] = time.monotonic):  # fmt: skip
        self.source, self.settings, self.ledger = source, settings, ledger or MemoryLedger()
        self.sleep, self.clock = sleep, clock
        self._last: float | None = None
        self._slots: deque[float] = deque()  # start times of calls in the last minute (reserved, maybe still ahead)
        self._lock = threading.Lock()

    def acquire(self) -> None:
        """Waits for this call's turn and counts it; raises Deferred (nothing counted) when the day's budget is spent or
        the wait would exceed `max_wait_seconds`."""
        with self._lock:
            s = self.settings
            if s.per_day is not None and self.ledger.used_today() >= s.per_day:
                raise Deferred(self.source, f"daily budget of {s.per_day} calls is spent")
            now = self.clock()
            start = self._next_start(now)
            if start - now > s.max_wait_seconds:
                raise Deferred(self.source, f"rate limit: would have to wait {start - now:.0f} s")
            self._last = start
            if s.per_minute is not None:  # only a per-minute budget reads the window; otherwise it would grow for ever
                self._slots.append(start)
            self.ledger.record()
        if start > now:
            self.sleep(start - now)

    def _next_start(self, now: float) -> float:
        s = self.settings
        start = now if self._last is None else max(now, self._last + s.min_spacing_seconds)
        if s.per_minute is not None:
            while self._slots and start - self._slots[0] >= MINUTE_SECONDS:
                self._slots.popleft()
            if len(self._slots) >= s.per_minute:
                start = max(start, self._slots[0] + MINUTE_SECONDS)
        return start
