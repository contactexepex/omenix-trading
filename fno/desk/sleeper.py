"""The real `Waiter` (story E3): sleeps until a moment of the timetable, at once when it has passed."""

from __future__ import annotations

import time as clock_time
from collections.abc import Callable
from datetime import datetime

from .daily_ports import Waiter


class SleepingWaiter(Waiter):
    def __init__(self, now: Callable[[], datetime], sleep: Callable[[float], None] = clock_time.sleep):
        self.now, self.sleep = now, sleep

    def until(self, moment: datetime) -> None:
        seconds = (moment - self.now()).total_seconds()
        if seconds > 0:
            self.sleep(seconds)
