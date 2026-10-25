"""The probe's session (story MS-P0b section 4): refuse a non-trading day, a kept-clear day and a sixth session;
stop a source for good once it was stopped on two sessions; then run each slot not yet run at its time, skip one more
than 2 minutes late, and stop each at its hard stop. A slot already in the counts file is never run again."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime

from ..models import IST
from .constants import (
    BLACKOUT_DAYS,
    BLACKOUT_LINE,
    DAY_DONE,
    HARD_STOP,
    LATE_START,
    MAX_SESSIONS,
    NOT_A_SESSION,
    SESSIONS_DONE,
    SLOT_SKIPPED,
    SLOTS,
    STOPPED_FOR_GOOD,
    STOPPED_SESSIONS_FOR_GOOD,
    Source,
)
from .counts import CountsFolder
from .slot import SlotRunner


class ProbeDay:
    def __init__(self, is_trading_day: Callable[[date], bool], folder: CountsFolder, slots: SlotRunner,
                 wall_clock: Callable[[], datetime], sleep: Callable[[float], None]):  # fmt: skip
        self.is_trading_day, self.folder, self.slots = is_trading_day, folder, slots
        self.wall_clock, self.sleep = wall_clock, sleep

    def run(self, session: date, out=print) -> int:
        """0 when the day ran clean or was not a probe day; 1 on any stop or refusal of a sixth session."""
        if not self.is_trading_day(session):
            out(NOT_A_SESSION)
            return 0
        if session in BLACKOUT_DAYS:
            out(BLACKOUT_LINE.format(day=session))
            return 0
        counts, earlier = self.folder.read(session), self.folder.earlier(session)
        done = sum(1 for other in earlier if other.started())
        if done >= MAX_SESSIONS and not counts.started():
            out(SESSIONS_DONE.format(count=done))
            return 1
        for source in Source:
            blocked = sum(1 for other in earlier if source in other.stops)
            if blocked >= STOPPED_SESSIONS_FOR_GOOD:
                self.slots.tools.disabled.add(source)
                out(STOPPED_FOR_GOOD.format(source=source, count=blocked))
        for slot in SLOTS:
            name = slot.strftime("%H:%M")
            if name in counts.slots:
                continue
            start = datetime.combine(session, slot, IST)
            now = self.wall_clock()
            if now > start + LATE_START:
                out(SLOT_SKIPPED.format(slot=name))
                continue
            if now < start:
                self.sleep((start - now).total_seconds())
            for line in self.slots.run(session, name, counts, start + HARD_STOP):
                out(line)
        out(DAY_DONE.format(day=session, groww=counts.spent(Source.GROWW), nse=counts.spent(Source.NSE)))
        return 1 if counts.stops or self.slots.tools.disabled else 0
