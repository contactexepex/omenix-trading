"""The daily run's log (story E3 criterion 6): `journal/runs/<date>.json` holds, for every step, its start and end
time, its inputs and its result, in the order the steps ran. It is rewritten whole after each step (written to a
temporary file, then renamed) and committed, so a restarted run reads which steps are done and repeats none of them.
A step failed by an unexpected error and marked `retry` is not done (DRY2 SF1, orchestrator 24 Oct): a same-day rerun
runs it again and its new entry replaces the failed one; a step that finished, or was refused, is never replaced."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from ..constants import JOURNAL_FOLDER, STEP_FAILED, STEP_REFUSED

RUNS_FOLDER = "runs"
PROBLEMS = (STEP_FAILED, STEP_REFUSED)
RETRY = "retry"  # a failed step's result key: true when a same-day rerun runs the step again


@dataclass
class RunLog:
    day: date
    path: Path
    steps: dict[str, dict] = field(default_factory=dict)

    @classmethod
    def open(cls, root: Path, day: date) -> RunLog:
        path = Path(root) / JOURNAL_FOLDER / RUNS_FOLDER / f"{day.isoformat()}.json"
        steps = json.loads(path.read_text(encoding="utf-8"))["steps"] if path.is_file() else {}
        return cls(day, path, steps)

    @staticmethod
    def days(root: Path) -> list[date]:
        """Every day with a run log (hidden files, such as the pending-commit marker, are not logs)."""
        folder = Path(root) / JOURNAL_FOLDER / RUNS_FOLDER
        names = (p.stem for p in folder.glob("*.json") if not p.name.startswith(".")) if folder.is_dir() else ()
        return sorted(date.fromisoformat(name) for name in names)

    def done(self, step: str) -> bool:
        """Recorded for good: an entry failed and marked for a retry is not done."""
        return step in self.steps and not _retried(self.steps[step]["result"])

    def result(self, step: str) -> dict:
        return self.steps[step]["result"]

    def record(self, step: str, started: datetime, finished: datetime, inputs: dict, result: dict) -> None:
        if self.done(step):
            raise ValueError(f"{self.day} step {step} is already recorded: a run never repeats a step")
        self.steps.pop(step, None)  # a retried step's failed entry: the new one goes last, in the order steps ran
        self.steps[step] = {"started_at": started.isoformat(), "finished_at": finished.isoformat(),
                            "inputs": inputs, "result": result}  # fmt: skip
        self._write()

    def _write(self) -> None:
        body = {"day": self.day.isoformat(), "kind": "daily_run", "steps": self.steps}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(f".{self.path.name}.tmp")
        temporary.write_text(json.dumps(body, indent=1, sort_keys=False) + "\n", encoding="utf-8")
        os.replace(temporary, self.path)


def problem_steps(steps: dict[str, dict]) -> list[tuple[str, str]]:
    """Each step that failed or was refused, with its status, in the order the steps ran: the one rule the run's last
    line and the card read (DRY2 R2, T1d)."""
    return [(name, step["result"]["status"]) for name, step in steps.items() if _problem(step["result"])]


def book_results(result: dict) -> dict:
    """A per-book step's result (the decisions, the exits) as book -> entry; {} when the step itself failed or was
    refused (DRY2 R2): its `{"status", "reason"}` is never read as books."""
    return {} if _problem(result) else result


def retried_steps(steps: dict[str, dict]) -> list[str]:
    """Each step a same-day rerun runs again (failed and marked `retry`), in the order the steps ran."""
    return [name for name, step in steps.items() if _retried(step["result"])]


def _retried(result: dict) -> bool:
    return result.get("status") == STEP_FAILED and result.get(RETRY) is True


def _problem(result: dict) -> bool:
    return result.get("status") in PROBLEMS
