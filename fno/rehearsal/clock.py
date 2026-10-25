"""The replay clock: the wall clock plus one offset, kept in a file every process of the rehearsal reads, so the
parent and its children always agree. Starting it puts "now" at the routine's time on the replayed day; a wait the
rehearsal skips moves the offset forward for every process at once. It never moves back."""

from __future__ import annotations

import os
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path

from ..models import wall_clock

OFFSET_FILE = "clock_offset_seconds"


class ReplayClock:
    def __init__(self, state: Path, wall: Callable[[], datetime] = wall_clock):
        self.path, self.wall = Path(state) / OFFSET_FILE, wall

    def start(self, at: datetime) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._write((at - self.wall()).total_seconds())

    def __call__(self) -> datetime:
        return self.wall() + timedelta(seconds=self._offset())

    def jump_to(self, moment: datetime) -> None:
        """Skips a wait: `moment` becomes now for every process; a moment already past changes nothing."""
        ahead = (moment - self()).total_seconds()
        if ahead > 0:
            self._write(self._offset() + ahead)

    def _offset(self) -> float:
        return float(self.path.read_text(encoding="utf-8"))

    def _write(self, seconds: float) -> None:
        part = self.path.with_suffix(".tmp")
        part.write_text(repr(seconds), encoding="utf-8")
        os.replace(part, self.path)  # atomic: a child never reads half a number
