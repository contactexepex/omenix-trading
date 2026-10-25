"""A download job's run summary (story O6): what the download step reported and what happened to every batch (the
run's progress manifest), saved once per run in Drive under `runs/<job>/<YYYY>/<MM>/<run id>.json`, plus the one
line posted to #fno-desk."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime

from ..storage.raw_store import RawFileStore
from .dispatcher import ALREADY_FIRED, FIRED_NOW, DispatchReport

REPORT_LINE = (
    "Omenix F&O {job} (GitHub Actions run {run_id}): download {download}; {batches} batches in window, "
    "{fired} fired to {routine}, {skipped} already fired, {failed} failed{notes}"
)


@dataclass(frozen=True)
class RunSummary:
    job: str
    run_id: str  # GitHub's run ID and attempt, so a re-run never overwrites a summary
    routine: str
    download: str  # the download step's outcome as the workflow reports it (success, failure, skipped)
    started: datetime
    finished: datetime
    report: DispatchReport
    notes: tuple[str, ...] = ()  # the download command's own result lines, as printed

    def to_json(self) -> bytes:
        body = {
            "job": self.job,
            "run_id": self.run_id,
            "routine": self.routine,
            "download": self.download,
            "started": self.started.isoformat(timespec="seconds"),
            "finished": self.finished.isoformat(timespec="seconds"),
            "notes": list(self.notes),
            "batches": [
                {"pointer": o.pointer.to_text(), "outcome": o.outcome, "detail": o.detail} for o in self.report.outcomes
            ],
        }
        return json.dumps(body, indent=1, sort_keys=True).encode()

    def line(self) -> str:
        notes = "".join(f"; {note}" for note in self.notes)
        return REPORT_LINE.format(
            job=self.job,
            run_id=self.run_id,
            download=self.download,
            batches=len(self.report.outcomes),
            fired=self.report.count(FIRED_NOW),
            routine=self.routine,
            skipped=self.report.count(ALREADY_FIRED),
            failed=len(self.report.failures),
            notes=notes,
        )


class RunSummaryStore:
    def __init__(self, store: RawFileStore):
        self.store = store

    @staticmethod
    def path_for(summary: RunSummary) -> str:
        return f"runs/{summary.job}/{summary.started:%Y}/{summary.started:%m}/{summary.run_id}.json"

    def save(self, summary: RunSummary) -> str:
        path = self.path_for(summary)
        self.store.put(path, summary.to_json())
        return path
