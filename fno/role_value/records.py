"""Where the two decisions' D3 records are read (story F9a): the real decision is the book's run collected in E3's run
log that day (S3's `CommittedRuns`, imported); the shadow decision is the run F9b writes under
`journal/<book>/role_value/shadow/<day>/<decision id>/`, in the same one-file-per-opportunity form."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import date
from pathlib import Path

from ..constants import JOURNAL_FOLDER
from ..playbook.decision_store import INPUTS_FILE
from ..scoreboard.committed_runs import CommittedRuns

SHADOW_FOLDER = "role_value/shadow"


class DecisionRecords(ABC):
    @abstractmethod
    def records(self, book: str, day: date, decision_id: str) -> list[dict] | None:
        """The decision's records, one per opportunity; None when there is no such decision."""


def _read_folder(folder: Path) -> list[dict] | None:
    if not folder.is_dir():
        return None
    paths = sorted(p for p in folder.glob("*.json") if p.name != INPUTS_FILE)
    return [json.loads(p.read_text(encoding="utf-8")) for p in paths]


class CollectedRunRecords(DecisionRecords):
    """Only a run the day's log collected on time was the book's decision (E3's late rule, S3's reading)."""

    def __init__(self, runs: CommittedRuns):
        self.runs = runs

    def records(self, book: str, day: date, decision_id: str) -> list[dict] | None:
        for run in self.runs.runs():
            if (run.book, run.day, run.run_id) == (book, day, decision_id) and run.on_time:
                return self.runs.records(run)
        return None


class ShadowRecordFiles(DecisionRecords):
    def __init__(self, root: Path):
        self.root = Path(root)

    def records(self, book: str, day: date, decision_id: str) -> list[dict] | None:
        return _read_folder(self.root / JOURNAL_FOLDER / book / SHADOW_FOLDER / day.isoformat() / decision_id)
