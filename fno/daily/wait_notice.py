"""Story O1-day-lock: every wait of a minute or more says so before it starts, so a routine watching the output can
tell a wait from a hang (23 Oct: a 7-minute wait for A4h's 15:40 read was taken for a hang and a second run started).
A wait for a moment already announced is not repeated, so a loop polling towards one moment prints one line."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta

from ..desk.daily_ports import Waiter

WAITING = "waiting until {moment:%H:%M} IST (the next step's time; not a hang, never stop the run)"
ANNOUNCED_FROM = timedelta(minutes=1)


class AnnouncedWaiter(Waiter):
    def __init__(self, waiter: Waiter, now: Callable[[], datetime], say: Callable[[str], None]):
        self.waiter, self.now, self.say = waiter, now, say
        self.announced: datetime | None = None

    def until(self, moment: datetime) -> None:
        if moment - self.now() >= ANNOUNCED_FROM and moment != self.announced:
            self.announced = moment
            self.say(WAITING.format(moment=moment))
        self.waiter.until(moment)
