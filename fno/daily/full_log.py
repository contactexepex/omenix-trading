"""Story O1-status-only: the daily run's full step results, text and child output included, kept off the repository.
`journal/runs/.full/<date>.json` is git-ignored (`.gitignore`), for the same container's reruns and for debugging;
the committed `journal/runs/<date>.json` holds the public form only (`PublicResult`)."""

from __future__ import annotations

import json
import os
from datetime import date, datetime
from pathlib import Path

from ..desk.run_log import RunLog
from ..desk.step_recorder import StepRecorder
from .public_log import PublicResult

FULL_LOGS = "journal/runs/.full"  # git-ignored: never committed


class FullRunLog:
    def __init__(self, folder: Path):
        self.folder = folder

    def path(self, day: date) -> Path:
        return self.folder / f"{day.isoformat()}.json"

    def record(self, day: date, name: str, step: dict) -> None:
        path = self.path(day)
        body = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {"day": day.isoformat(), "steps": {}}
        body["steps"][name] = step
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.tmp")
        temporary.write_text(json.dumps(body, indent=1, default=str) + "\n", encoding="utf-8")
        os.replace(temporary, path)


class PublicRecorder(StepRecorder):
    """The full result into the private log first, then its public form into the committed run log."""

    def __init__(self, public: PublicResult, full: FullRunLog):
        self.public, self.full = public, full

    def record(self, log: RunLog, name: str, started: datetime, finished: datetime, inputs: dict, result: dict) -> None:
        times = {"started_at": started.isoformat(), "finished_at": finished.isoformat()}
        self.full.record(log.day, name, times | {"inputs": inputs, "result": result})
        log.record(name, started, finished, self.public.public(name, inputs), self.public.public(name, result))
