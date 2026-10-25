"""Every request of a source's slot goes through one `PacedCaller` (story MS-P0b section 3): it refuses a request
past the slot's reservation or its hard stop, waits the pace, sends exactly one request, and applies the verdict: a
retry after its wait, a stop for the day, or a missing row. It counts every request it sends and how long each took."""

from __future__ import annotations

import statistics
from collections import Counter
from collections.abc import Callable
from datetime import datetime, timedelta

from .answers import RawAnswer, Verdict, judge
from .constants import RATE_LIMIT_WAIT_SECONDS, SERVER_ERROR_WAIT_SECONDS
from .pace import StudyPace


class SourceStopped(Exception):
    """The source is stopped for the day; `reason` is one plain line (a status, a class name or the cap)."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


class PacedCaller:
    def __init__(self, pace: StudyPace, allowed: int, deadline: datetime, wall_clock: Callable[[], datetime],
                 timer: Callable[[], float], sleep, first_429_stops: bool, earlier_429s: int = 0,
                 cap_reason: str = ""):  # fmt: skip
        """`allowed`: the requests this slot reserved; `cap_reason`: the stop line once they are used (the daily cap's
        line when the reservation was cut short by it, else empty: the slot just ends). `earlier_429s`: NSE's 429s
        earlier today, so a second one stops it."""
        self.pace, self.allowed, self.deadline, self.wall_clock = pace, allowed, deadline, wall_clock
        self.timer, self.sleep, self.first_429_stops = timer, sleep, first_429_stops
        self.cap_reason, self.rate_hits = cap_reason, earlier_429s
        self.sent, self.refusals, self.latency = 0, Counter(), {}

    def call(self, kind: str, request: Callable[[], RawAnswer]) -> RawAnswer | None:
        """The answer, or None when the row is missing (a 5xx twice, or no time left); raises `SourceStopped`."""
        retried_server = False
        while True:
            if not self._may_send():
                return None
            answer = self._send(kind, request)
            if answer is None:
                return None
            verdict, reason = judge(answer, self.first_429_stops)
            if verdict is Verdict.OK:
                return answer
            self.refusals[reason] += 1
            if verdict is Verdict.STOP:
                raise SourceStopped(reason)
            if verdict is Verdict.RETRY_RATE:
                self.rate_hits += 1
                if self.rate_hits > 1:
                    raise SourceStopped(f"second {reason} today")
                self._wait(RATE_LIMIT_WAIT_SECONDS)
            elif retried_server:
                return None
            else:
                retried_server = True
                self._wait(SERVER_ERROR_WAIT_SECONDS)

    def latency_ms(self) -> dict[str, float]:
        """Median and 95th percentile per kind of request, in milliseconds."""
        figures = {}
        for kind, values in sorted(self.latency.items()):
            ordered = sorted(values)
            figures[f"{kind}_median"] = round(statistics.median(ordered), 1)
            figures[f"{kind}_p95"] = round(ordered[min(len(ordered) - 1, int(0.95 * len(ordered)))], 1)
        return figures

    def _may_send(self) -> bool:
        if self.sent >= self.allowed:
            if self.cap_reason:
                raise SourceStopped(self.cap_reason)
            return False
        return True

    def _send(self, kind: str, request: Callable[[], RawAnswer]) -> RawAnswer | None:
        """None at or after the hard stop, checked after the pace's wait: nothing is sent past it (self-review 6)."""
        self.pace.wait_turn()
        if self.wall_clock() >= self.deadline:
            return None
        started = self.timer()
        self.sent += 1
        answer = request()
        self.latency.setdefault(kind, []).append((self.timer() - started) * 1000)
        return answer

    def _wait(self, seconds: float) -> None:
        """Waits, unless the wait would pass the slot's hard stop: then the slot ends now, never retried early."""
        if self.wall_clock() + timedelta(seconds=seconds) >= self.deadline:
            self.deadline = self.wall_clock()
            return
        self.sleep(seconds)
