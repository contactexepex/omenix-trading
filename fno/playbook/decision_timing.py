"""On time or late (story D3 criterion 5, design 12.6): a decision counts only if its records were committed before
the day's execution snapshot started. A run that is not committed, or committed at or after that moment, is late: it
is recorded as such and never filled (E4/E5 call `require_on_time` before any fill; E3 schedules the order)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Protocol

from ..desk.pack_items import available_time
from .decision_store import SUMS_FILE

ON_TIME, LATE = "on_time", "late"


class LateDecision(ValueError):
    """The decision was not committed before the execution snapshot: it is never filled."""


class CommitTimes(Protocol):
    def added_at(self, path: str) -> str | None: ...


def timeliness(run: Path, root: Path, snapshot_started_at: datetime, git: CommitTimes) -> tuple[str, str]:
    """(on_time or late, why) for a run folder, from the commit that added its `records.sha256`."""
    committed = git.added_at((run / SUMS_FILE).relative_to(root).as_posix())
    moment = available_time(committed) if committed else None
    if moment is None:
        return LATE, "not committed"
    if moment >= snapshot_started_at:
        return (
            LATE,
            f"committed {moment.isoformat()}, not before the execution snapshot {snapshot_started_at.isoformat()}",
        )
    return ON_TIME, f"committed {moment.isoformat()}, before the execution snapshot {snapshot_started_at.isoformat()}"


def require_on_time(run: Path, root: Path, snapshot_started_at: datetime, git: CommitTimes) -> None:
    status, why = timeliness(run, root, snapshot_started_at, git)
    if status == LATE:
        raise LateDecision(f"{run.name}: late ({why}); it is never filled")
