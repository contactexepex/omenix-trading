"""Story O1, gap F1 (judge 412 add. 2-3): each 3 pm part's recorder holds an exclusive `flock` on its own git-ignored
lock file for its whole life. The run takes the lock and hands the open file to the child (`pass_fds`), so A4's
commands are unchanged and the kernel frees the lock when the child dies; a pid lease is not used (pids are reused).
A rerun asks whether the lock is still held to know if a part of a crashed run is alive in this container."""

from __future__ import annotations

import contextlib
import fcntl
import os
from collections.abc import Iterator
from datetime import date, datetime
from pathlib import Path

PART_LOCKS = "journal/runs/.parts"  # git-ignored (.gitignore); no `.json` there, so no run-log reader takes it


class PartLocks:
    def __init__(self, folder: Path):
        self.folder = folder

    def path(self, day: date, name: str) -> Path:
        return self.folder / f"{day.isoformat()}_{name}.lock"

    @contextlib.contextmanager
    def taken(self, day: date, name: str, at: datetime) -> Iterator[int | None]:
        """The locked file's descriptor, with `at` (the part's start) written in it, for the child to inherit; None
        when a recorder still holds it. The run's own copy is closed on leaving, so only the child keeps the lock."""
        self.folder.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(self.path(day, name), os.O_RDWR | os.O_CREAT, 0o644)
        try:
            if not self._lock(descriptor):
                yield None
                return
            os.ftruncate(descriptor, 0)
            os.write(descriptor, at.isoformat().encode())
            yield descriptor
        finally:
            os.close(descriptor)

    def held(self, day: date, name: str) -> bool:
        """True while a living process holds the part's lock; the check takes the free lock and lets it go at once."""
        if not self.path(day, name).is_file():
            return False
        descriptor = os.open(self.path(day, name), os.O_RDWR)
        try:
            return not self._lock(descriptor)
        finally:
            os.close(descriptor)

    def started(self, day: date, name: str) -> str | None:
        """When the run that took the lock started the part (its own record, as an earlier run's output is gone)."""
        path = self.path(day, name)
        return (path.read_text(encoding="utf-8").strip() or None) if path.is_file() else None

    @staticmethod
    def _lock(descriptor: int) -> bool:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return False
        return True
