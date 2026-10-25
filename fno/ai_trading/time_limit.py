"""A hard time limit on an AI book's decider (story F1t; judge 651 should-fix 1): `ai_collect` must end before E3's
decision deadline, or E3's collection starts late and every book, Book 1 included, loses its day. The daily run is
one thread, so the limit is a real-time alarm in that thread: the decider is interrupted where it is, and the
promoter puts its write paths back. Outside the main thread no alarm can be set; the collector's own check after the
decider (a run finished at or after the deadline is undone and `late`) still holds there."""

from __future__ import annotations

import signal
import threading
from collections.abc import Iterator
from contextlib import contextmanager

TIMED_OUT = "the decider did not finish within {seconds:.1f} s, before E3's decision deadline"


class DecisionTimedOut(BaseException):
    """The decider was stopped by its time limit. A `BaseException`, as `KeyboardInterrupt` is (judge 651.1): a
    decider's own `except Exception` (Book 3's proposal guards have one) must never swallow the stop."""


@contextmanager
def time_limit(seconds: float | None) -> Iterator[None]:
    """Raises `DecisionTimedOut` in the block once `seconds` (real time) have passed; None sets no limit."""
    if seconds is None or threading.current_thread() is not threading.main_thread():
        yield
        return
    if seconds <= 0:
        raise DecisionTimedOut(TIMED_OUT.format(seconds=0))

    def expired(signum, frame):
        raise DecisionTimedOut(TIMED_OUT.format(seconds=seconds))

    previous = signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        try:
            signal.setitimer(signal.ITIMER_REAL, 0)  # first: no alarm can land after this line
        finally:
            signal.signal(signal.SIGALRM, previous)  # always, even if the alarm landed inside this `finally`
