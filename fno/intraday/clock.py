"""The host clock checked against GitHub and Slack on every mark (design 4.4's clock contract), through the shared
server-clock module (`fno/server_clock.py`, also T1's): only a 2xx or 3xx answer's `Date` is trusted, GitHub is asked
at a repository path (its API root answers an error through this environment's proxy), and a host time outside a
server's time by more than 5 s (plus its one-second resolution) is a WARNING. A server that gives no trusted time is
named on the reading, never silently skipped."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from ..server_clock import ServerClock, SkewCheck, check_server

CLOCK_OK, CLOCK_SKEW, CLOCK_PARTIAL, CLOCK_UNCHECKED = "clock_ok", "clock_skew", "clock_partial", "clock_unchecked"


@dataclass(frozen=True)
class ClockReading:
    status: str
    checks: tuple[SkewCheck, ...]

    @property
    def skews(self) -> dict[str, float]:
        """Server name -> how far the host clock fell outside its time, in seconds (servers that answered)."""
        return {c.server: c.skew_seconds for c in self.checks if c.skew_seconds is not None}

    @property
    def worst(self) -> float | None:
        return max(self.skews.values()) if self.skews else None

    def warning(self) -> str:
        """The lines to print when something is wrong (a skew, or a server not checked), else empty."""
        return "; ".join(c.line for c in self.checks if c.warning or c.skew_seconds is None)

    def day_cell(self) -> str:
        """A day row's clock cell: the warning, else "ok" only for a clock checked ok, else its status (a rehearsal's
        replay clock has no checks, so no warning, and is never recorded as "ok"; REH1l)."""
        return self.warning() or ("ok" if self.status == CLOCK_OK else self.status)


class ClockCheck:
    def __init__(self, servers: list[ServerClock], host_now: Callable[[], datetime]):
        self.servers, self.host_now = servers, host_now

    def check(self) -> ClockReading:
        checks = tuple(check_server(server, self.host_now) for server in self.servers)
        answered = [c for c in checks if c.skew_seconds is not None]
        if not answered:
            return ClockReading(CLOCK_UNCHECKED, checks)
        if any(c.warning for c in answered):
            return ClockReading(CLOCK_SKEW, checks)
        return ClockReading(CLOCK_OK if len(answered) == len(checks) else CLOCK_PARTIAL, checks)
