"""No Groww call inside A16's marks unless it is A16's own (story GW1, part 5).

A16 asks at 4 a second (`fno/intraday/groww_source.py`), close to Groww's 300 a minute Live Data cap (5 a second
averaged; research/school/probes/2026-10-22-p0-1-groww-chain.md). Every scheduled routine runs in its own container,
so no limiter is shared. The clock is the shared rule instead, for a provider built through `get_provider` (the 3 pm
NIFTY, `v4`, A4c and E3's execution captures): an attempt that starts in a mark's quiet window (from the mark to
`QUIET_SECONDS` after it) waits for its end before its first call (`wait`, from `GrowwProvider.expiries`, the first
Groww call of every A4 attempt), and any other call inside one is refused unsent (`check`). A call is never delayed
after its caller stamped its send time (A4's fetcher stamps before it asks): a refused call is a recorded failure with
true times, retried by its recorder. A16's marks took 48-58 s to record on 20-23 Oct, 83 s at most (its committed slot
rows' `first_seen_at` minus the mark)."""

from __future__ import annotations

import time as clock_module
from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import datetime, timedelta

from fno.ingestion.intraday.slots import marks
from fno.shared.models import now_ist

QUIET_SECONDS = 120  # 83 s at most at 5 a second; about 95 s expected at A16's 4 (GW1)
REFUSED = "Groww call refused unsent: inside A16's {mark:%H:%M} mark until {end:%H:%M:%S} IST"


class GrowwQuietWindow(RuntimeError):
    """A call came inside an A16 mark's quiet window; nothing reached Groww."""


class QuietWindows(ABC):
    @abstractmethod
    def wait(self) -> None:
        """Before an attempt's first call: returns when calls may start."""

    @abstractmethod
    def check(self) -> None:
        """Before any call: raises `GrowwQuietWindow` inside a quiet window."""


class MarkQuietWindows(QuietWindows):
    def __init__(self, clock: Callable[[], datetime] = now_ist, sleep: Callable[[float], None] = clock_module.sleep,
                 quiet: timedelta = timedelta(seconds=QUIET_SECONDS)):  # fmt: skip
        self.clock, self.sleep, self.quiet = clock, sleep, quiet

    def wait(self) -> None:
        now = self.clock()
        mark = self._mark_at(now)
        if mark is not None:
            self.sleep((mark + self.quiet - now).total_seconds())

    def check(self) -> None:
        mark = self._mark_at(self.clock())
        if mark is not None:
            raise GrowwQuietWindow(REFUSED.format(mark=mark, end=mark + self.quiet))

    def _mark_at(self, now: datetime) -> datetime | None:
        return next((m for m in marks(now.date()) if m <= now < m + self.quiet), None)


class NoQuietWindows(QuietWindows):
    """A16 and the readers that never meet its marks (pre-open, A16b's candles): calls start when asked."""

    def wait(self) -> None:
        return None

    def check(self) -> None:
        return None
