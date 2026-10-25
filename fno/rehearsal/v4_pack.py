"""Protocol v4's daily pieces in a rehearsal (story G10 completion, criterion 12), chosen by their composition roots:
unchanged in a real run. The release excuses a `system_late` today when the record holds no `v4` capture for the
replayed day (nothing failed: there is nothing to replay); the deadline checks the replayed day only (the rehearsal's
push log holds only its own pushes); and the one `v4_pack` note reaches the `v4` quote part's child process."""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping, Sequence
from datetime import date
from pathlib import Path

from ..constants import ENV_FNO_REHEARSAL_NOT_LIVE
from ..daily.processes import Processes
from .mode import rehearsal

NO_CAPTURE = "rehearsal: no v4 capture recorded for this day"


def rehearsed_release_excuse(recorded: Callable[[Path, date], bool], env: Mapping[str, str] = os.environ):
    """`recorded(record, day)`: whether the rehearsal's record checkout holds a `v4` attempt of `day`."""
    mode = rehearsal(env)
    if mode is None:
        return lambda day: None
    return lambda day: None if recorded(mode.record, day) else NO_CAPTURE


def rehearsed_catch_up(env: Mapping[str, str] = os.environ) -> bool:
    return rehearsal(env) is None


class NotedPartProcesses(Processes):
    """Starts a quote part's child with its own not-live note in the environment (`ENV_FNO_REHEARSAL_NOT_LIVE`), so its
    posts carry the same line as the steps sharing its live key; every other part starts with no note, even inside a
    noted step's wait (NIFTY starting during `v4_release`'s wait)."""

    def __init__(self, processes, notes: Mapping[tuple[str, ...], str]):
        self.processes, self.notes = processes, notes

    def start(self, arguments: Sequence[str], hold: int | None = None):
        note = self.notes.get(tuple(arguments))
        before = os.environ.get(ENV_FNO_REHEARSAL_NOT_LIVE)
        if note is None:  # a part started during a noted step's wait never takes that step's note
            os.environ.pop(ENV_FNO_REHEARSAL_NOT_LIVE, None)
        else:
            os.environ[ENV_FNO_REHEARSAL_NOT_LIVE] = note
        try:
            return self.processes.start(arguments, hold)
        finally:
            if before is None:
                os.environ.pop(ENV_FNO_REHEARSAL_NOT_LIVE, None)
            else:
                os.environ[ENV_FNO_REHEARSAL_NOT_LIVE] = before


def rehearsed_part_processes(processes, notes: Mapping[tuple[str, ...], str]):
    """The parts' processes, noted when a part's live key is not live in real runs (a rehearsal only)."""
    return NotedPartProcesses(processes, notes) if notes else processes
