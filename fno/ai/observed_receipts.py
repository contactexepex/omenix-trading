"""Receipts by observation at the deadline (story F1t; E3's judge-82 rule applied to sealed answers): a file counts as
received at a deadline only if the remote branch, read at that deadline, already contained its commit. The readings
come from `remote_observer.py`, a child process that reads the remote at each deadline whatever the caller is doing.
A commit's own date is never used, and no GitHub API is called. A reading that failed, or started more than
`GRACE` after its deadline, proves nothing, so a commit seen only there is `ReceiptUnknown` (callers treat it as late).
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Protocol

from .receipts import PushReceipts, ReceiptUnknown

GRACE = timedelta(seconds=30)
NOT_SEEN = "{commit} was not on the remote at any valid reading ({readings})"
NO_READING = "no valid reading of the remote: {why}"


class Ancestry(Protocol):
    def is_ancestor(self, older: str, newer: str) -> bool: ...


@dataclass(frozen=True)
class Observation:
    """One reading of the remote branch, taken for `deadline`; `commit` is None when the reading failed."""

    deadline: datetime
    started_at: datetime
    ended_at: datetime
    commit: str | None
    error: str = ""

    def problem(self) -> str:
        """Why this reading proves nothing, or '' when it is valid."""
        if self.commit is None:
            return f"the reading for {self.deadline.isoformat()} failed ({self.error or 'no reason given'})"
        if self.started_at - self.deadline > GRACE:
            late = (self.started_at - self.deadline).total_seconds()
            return f"the reading for {self.deadline.isoformat()} started {late:.0f} s after it (over {GRACE.seconds} s)"
        if self.started_at < self.deadline:
            return f"the reading for {self.deadline.isoformat()} started before it"
        return ""

    def to_json(self) -> dict:
        return {key: value.isoformat() if isinstance(value, datetime) else value for key, value in asdict(self).items()}

    @classmethod
    def from_json(cls, fields: dict) -> Observation:
        times = {key: datetime.fromisoformat(fields[key]) for key in ("deadline", "started_at", "ended_at")}
        return cls(**times, commit=fields.get("commit"), error=fields.get("error", ""))


class ObservationFile:
    """The readings of one day, as the observer writes them (replaced whole after each reading)."""

    def __init__(self, path: Path):
        self.path = Path(path)

    def read(self) -> list[Observation]:
        if not self.path.is_file():
            return []
        return [Observation.from_json(item) for item in json.loads(self.path.read_text(encoding="utf-8"))]

    def append(self, observation: Observation) -> None:
        readings = [o.to_json() for o in self.read()] + [observation.to_json()]
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(f".{self.path.name}.tmp")
        temporary.write_text(json.dumps(readings, indent=1) + "\n", encoding="utf-8")
        temporary.replace(self.path)


class ObservedPushes(PushReceipts):
    """`received_at(commit)` is the deadline of the first valid reading that contains the commit."""

    def __init__(self, observations: Sequence[Observation], history: Ancestry):
        self.observations = sorted(observations, key=lambda o: o.deadline)
        self.history = history

    def received_at(self, commit: str) -> datetime:
        valid = [o for o in self.observations if not o.problem()]
        if not valid:
            why = "; ".join(o.problem() for o in self.observations) or "none was taken"
            raise ReceiptUnknown(NO_READING.format(why=why))
        for observation in valid:
            if self.history.is_ancestor(commit, observation.commit):
                return observation.deadline
        readings = ", ".join(o.deadline.strftime("%H:%M:%S") for o in valid)
        raise ReceiptUnknown(NOT_SEEN.format(commit=commit[:10], readings=readings))

    def valid_at(self, deadline: datetime) -> Observation | None:
        """The valid reading taken for `deadline`, if there is one."""
        return next((o for o in self.observations if o.deadline == deadline and not o.problem()), None)
