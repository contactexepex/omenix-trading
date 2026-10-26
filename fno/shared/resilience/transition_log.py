"""A circuit breaker's memory across runs (story R1): one append-only CSV per source, one row per TRANSITION (opened,
half_open, reopened, closed), never per failed call. Every scheduled run is a new process, so without this an open
breaker would be forgotten and the next run would call a blocking source again.

Committed with the run's other logs and listed in `.gitattributes` with `merge=union`, so jobs that append at once keep
both sides' rows. A lost row fails open: the next run calls the source and its own failures re-open the breaker."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

FIELDS = ("at", "source", "event", "cool_down_seconds")
OPENED, HALF_OPEN, REOPENED, CLOSED = "opened", "half_open", "reopened", "closed"


@dataclass(frozen=True)
class Transition:
    at: datetime
    source: str
    event: str
    cool_down_seconds: float


class TransitionLog:
    def __init__(self, path: Path):
        self.path = Path(path)

    def append(self, transition: Transition) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        new = not self.path.is_file()
        with self.path.open("a", encoding="utf-8", newline="") as file:
            writer = csv.writer(file, lineterminator="\n")
            if new:
                writer.writerow(FIELDS)
            writer.writerow(
                [transition.at.isoformat(), transition.source, transition.event, transition.cool_down_seconds]
            )

    def rows(self, source: str) -> list[Transition]:
        if not self.path.is_file():
            return []
        text = self.path.read_text(encoding="utf-8")
        found = [
            Transition(datetime.fromisoformat(r["at"]), r["source"], r["event"], float(r["cool_down_seconds"]))
            for r in csv.DictReader(io.StringIO(text))
            if r["source"] == source
        ]
        return sorted(found, key=lambda t: t.at)  # union-merged files are not in time order

    def last(self, source: str) -> Transition | None:
        rows = self.rows(source)
        return rows[-1] if rows else None


class LayeredLog(TransitionLog):
    """A committed log that a run only reads, and a run-local file that it appends to (story R1b2). Writing the
    committed file during a run would leave a tracked file modified, and a `git pull --no-rebase` by another
    committer of the same run then refuses. The run-local file is git-ignored and merged into the committed one by
    the run's last step. Reads see both."""

    def __init__(self, committed: Path, local: Path):
        super().__init__(local)
        self.committed = TransitionLog(committed)

    def rows(self, source: str) -> list[Transition]:
        return sorted([*self.committed.rows(source), *super().rows(source)], key=lambda t: t.at)
