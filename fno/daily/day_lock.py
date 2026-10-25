"""Story O1-day-lock (A4h builder's finding, 23 Oct 2026): one `daily run` per day per container. The run holds an
exclusive `flock` on the day's git-ignored lock file for its whole life; the kernel frees it when the process dies,
so a rerun after a crash or a kill goes on, while a second run beside a living one does nothing. On 23 Oct a
routine took a 7-minute wait for a hang, started a rerun beside the living run, and both read and uploaded the same
close file to Drive. The descriptor is not inherited (Python's default), so no child keeps the lock."""

from __future__ import annotations

import contextlib
import fcntl
import os
from collections.abc import Iterator
from datetime import date, datetime
from pathlib import Path

ALREADY_RUNNING = (
    "another daily run of {day} is running in this container (since {since}): this run did nothing; wait for its "
    "last line, never stop it while it prints"
)


class DayLock:
    def __init__(self, folder: Path):
        self.folder = Path(folder)

    def path(self, day: date) -> Path:
        return self.folder / f"{day.isoformat()}_run.lock"

    @contextlib.contextmanager
    def taken(self, day: date, at: datetime) -> Iterator[str | None]:
        """None while this run holds the day; otherwise the living run's start time, and this run holds nothing."""
        self.folder.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(self.path(day), os.O_RDWR | os.O_CREAT, 0o644)
        try:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                yield os.pread(descriptor, 64, 0).decode(errors="replace").strip() or "unknown"
                return
            os.ftruncate(descriptor, 0)
            os.pwrite(descriptor, at.isoformat(timespec="seconds").encode(), 0)
            yield None
        finally:
            os.close(descriptor)  # closing the descriptor frees the lock
