"""A rehearsal's waits (owner, 24 Oct: accelerated, the windows at real speed): while no 3 pm part is running, a wait
moves the shared replay clock straight to its moment; while one is, time runs at real speed, so each capture window
behaves as on the day. Every wait still goes through the run's own waiter, so the parts are serviced as ever."""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from datetime import datetime, timedelta

from ..desk.daily_ports import Waiter
from ..models import now_utc
from .clock import ReplayClock
from .mode import rehearsal

REAL_SPEED_STEP = timedelta(seconds=5)


class SkippingWaiter(Waiter):
    """`recording`: a part's recorder is running (real speed); `next_start`: the next moment a part may start, which a
    skip never passes, so a part still starts at its own time (14:38)."""

    def __init__(self, inner: Waiter, now: Callable[[], datetime], jump_to: Callable[[datetime], None],
                 recording: Callable[[], bool], next_start: Callable[[], datetime | None]):  # fmt: skip
        self.inner, self.now, self.jump_to = inner, now, jump_to
        self.recording, self.next_start = recording, next_start

    def until(self, moment: datetime) -> None:
        while self.now() < moment:
            if self.recording():
                self.inner.until(min(moment, self.now() + REAL_SPEED_STEP))
                continue
            start = self.next_start()
            if start is not None and start <= self.now():
                self.inner.until(self.now())  # services the parts: the one due now starts here
                if self.recording() or self.next_start() != start:
                    continue  # it started (or ended at once): carry on from there
            before = self.now()
            self.jump_to(moment if start is None or start <= before else min(moment, start))
            if self.now() <= before:  # this process's clock is not the replay clock: wait for real, never spin
                break
            self.inner.until(self.now())
        self.inner.until(moment)


def rehearsed_waiter(waiter: Waiter, parts, env: Mapping[str, str] = os.environ) -> Waiter:
    """The daily run's waiter, chosen in its composition root: a rehearsal skips the waits outside the windows."""
    mode = rehearsal(env)
    if mode is None:
        return waiter
    return SkippingWaiter(waiter, now_utc, ReplayClock(mode.state).jump_to, parts.recording, parts.next_start)
