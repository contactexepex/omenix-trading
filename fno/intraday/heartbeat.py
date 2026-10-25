"""The recorder's heartbeat (story A16, design 4.2): every run writes when it started and finished, so a silent host
is detectable. The check, run by another job, reports "silent" (a WARNING alert, design 6.5) when the last finish is
more than 30 minutes old during a recorded session's watched hours."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from pathlib import Path

from ..models import IST
from .document import parse_time

FILE_NAME = "heartbeat.json"
SILENT_AFTER = timedelta(minutes=30)
WATCH_FROM, WATCH_TO = time(9, 45), time(15, 45)  # 30 minutes after the first mark, 15 after the last
OK, SILENT, NOT_WATCHED = "ok", "silent", "not watched"
SILENT_ALERT = (
    "Action: check the 15-minute recorder's routine (story A16). WARNING, monitor silent: {detail}. Snapshots missed "
    "meanwhile stay gaps."
)


@dataclass(frozen=True)
class HeartbeatState:
    status: str
    line: str


class Heartbeat:
    def __init__(self, folder: Path):
        self.file = Path(folder) / FILE_NAME

    def write(self, beat: dict) -> None:
        self.file.parent.mkdir(parents=True, exist_ok=True)
        self.file.write_text(json.dumps(beat, indent=1, sort_keys=True) + "\n", encoding="utf-8")

    def read(self) -> dict | None:
        return _parse(self.file.read_text(encoding="utf-8")) if self.file.is_file() else None


class PublishedHeartbeat:
    """GitHub's copy of the heartbeat (`origin/<branch>`), read by the silence check: a host whose pushes fail must
    not look alive from its own working tree. None when it cannot be fetched or read (the check then says silent)."""

    def __init__(self, repository: Path, path: str, branch: str = "main", run=subprocess.run):
        self.repository, self.path, self.branch, self.run = Path(repository), path, branch, run

    def read(self) -> dict | None:
        fetched = self._git("fetch", "-q", "origin", self.branch)
        shown = self._git("show", f"origin/{self.branch}:{self.path}") if fetched.returncode == 0 else fetched
        return _parse(shown.stdout) if shown.returncode == 0 else None

    def _git(self, *args: str) -> subprocess.CompletedProcess:
        return self.run(["git", *args], cwd=self.repository, capture_output=True, text=True)


def _parse(text: str) -> dict | None:
    try:
        beat = json.loads(text)
    except ValueError:
        return None
    return beat if isinstance(beat, dict) else None


def heartbeat_state(beat: dict | None, now: datetime, recorded_session: bool) -> HeartbeatState:
    """Silent when, on a recorded session between 09:45 and 15:45 IST, the last run finished over 30 minutes ago."""
    local = now.astimezone(IST)
    if not recorded_session or not WATCH_FROM <= local.time() <= WATCH_TO:
        return HeartbeatState(NOT_WATCHED, f"{NOT_WATCHED}: not a recorded session's watched hours")
    finished = _finished(beat)
    if finished is None:
        return HeartbeatState(SILENT, f"{SILENT}: no readable heartbeat")
    age = now - finished
    status = SILENT if age > SILENT_AFTER else OK
    minutes = age.total_seconds() / 60
    return HeartbeatState(status, f"{status}: last run finished {finished.astimezone(IST):%Y-%m-%d %H:%M} IST, "
                                  f"{minutes:.0f} minutes ago")  # fmt: skip


def _finished(beat: dict | None) -> datetime | None:
    try:
        return parse_time(str(beat.get("run_finished_at", ""))) if beat else None
    except ValueError:
        return None
