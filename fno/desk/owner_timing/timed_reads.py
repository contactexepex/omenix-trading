"""The fill step's time limit (story E8 rule 11; judge D, judge 178 addendum 5; judge 193 addenda 4 and 6).

A timer cannot stop a thread stuck inside a Drive or A16 read, and many HTTP clients time out only each wait for
data, so a server that trickles bytes can outlast them. So every call through `TimedStore` runs in its own daemon
thread and is abandoned when it has not returned within its cap of the whole call (60 seconds) or the step's
remaining time (10 minutes, O1's part limit), whichever ends first. An abandoned call raises `StepTimedOut`, which the
step treats as a failure: new entries fail closed and exits still run. The abandoned thread can finish later; its
result is ignored. Only reads go through it: an abandoned write could still land after the step moved on and overwrite
later work, so `put` refuses (judge 203, sf 2)."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import TypeVar

from ...storage.index_store import IndexFileStore
from ...storage.raw_store import RawFileStore, ReadOnlyStoreError

READ_CAP_SECONDS = 60.0
STEP_LIMIT_SECONDS = 600.0  # O1's 10-minute part limit
TIMED_OUT = "{what} did not finish within {seconds:.0f} s (the fill step's time limit)"
READ_ONLY = "the fill step's timed store only reads; writes go to write-once paths after every read (not {path})"

T = TypeVar("T")


class StepTimedOut(TimeoutError):
    """A read outlasted its cap or the step's deadline: the step fails, new entries fail closed."""


class StepDeadline:
    def __init__(self, limit_seconds: float = STEP_LIMIT_SECONDS, clock: Callable[[], float] = time.monotonic):
        self.clock, self.limit = clock, limit_seconds
        self.ends = clock() + limit_seconds

    def restart(self) -> None:
        """The limit counts from the step's start, not from when the run was built."""
        self.ends = self.clock() + self.limit

    def remaining(self) -> float:
        return self.ends - self.clock()


def call_within(what: str, call: Callable[[], T], seconds: float) -> T:
    """`call()`'s result, or `StepTimedOut` when the whole call has not returned within `seconds`."""
    if seconds <= 0:
        raise StepTimedOut(TIMED_OUT.format(what=what, seconds=0))
    outcome: dict = {}

    def run() -> None:
        try:
            outcome["value"] = call()
        except BaseException as exc:  # handed back to the caller's thread below
            outcome["error"] = exc

    worker = threading.Thread(target=run, name=f"e8-read {what}", daemon=True)
    worker.start()
    worker.join(seconds)
    if worker.is_alive():
        raise StepTimedOut(TIMED_OUT.format(what=what, seconds=seconds))
    if "error" in outcome:
        raise outcome["error"]
    return outcome["value"]


class TimedStore(RawFileStore):
    """Any store, read-only, with every read capped (decorator): the step's only way to read Drive."""

    def __init__(self, store: RawFileStore, deadline: StepDeadline, cap_seconds: float = READ_CAP_SECONDS):
        self.store, self.deadline, self.cap = store, deadline, cap_seconds
        self.name = f"timed {store.name}"

    def get(self, path: str) -> bytes | None:
        return self._timed(f"reading {path}", lambda: self.store.get(path))

    def put(self, path: str, data: bytes) -> None:
        raise ReadOnlyStoreError(READ_ONLY.format(path=path))

    def checksums(self, folder: str) -> dict[str, str]:
        return self._timed(f"listing {folder}", lambda: self.store.checksums(folder))

    def folders(self, folder: str) -> list[str]:
        return self._timed(f"listing {folder}", lambda: self.store.folders(folder))

    def _timed(self, what: str, call: Callable[[], T]) -> T:
        return call_within(what, call, min(self.cap, self.deadline.remaining()))


class TimedIndexStore(IndexFileStore):
    """E2c's private-records store for the step's account writes: each pull capped like any read, each push made in
    full (a write is never abandoned, judge 203 should-fix 2; the pushes come after that item's reads)."""

    def __init__(self, store: IndexFileStore, deadline: StepDeadline, cap_seconds: float = READ_CAP_SECONDS):
        self.store, self.deadline, self.cap = store, deadline, cap_seconds

    def get(self, path: str) -> bytes | None:
        return call_within(f"reading {path}", lambda: self.store.get(path), min(self.cap, self.deadline.remaining()))

    def replace(self, path: str, data: bytes) -> None:
        self.store.replace(path, data)
