"""Where a book's runs of a day already are (story E5b, decision 59 a): one Book 1 decision a day. Before deciding,
Book 1 fetches origin and looks in three places: origin's decision folder, this checkout's `HEAD` and the day folder
on disk. A run found anywhere means the day is decided, whatever the inputs. A run on disk only (neither committed nor
recorded by the pending marker) is named for the owner's hand fix, never quietly taken as "already decided"."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date

from ..desk.daily_ports import CommitFailed
from ..desk.git_sync import Git, GitError
from ..playbook.decision_store import INPUTS_FILE, DecisionStore

ON_ORIGIN, COMMITTED, ON_DISK = "on origin", "committed here, not pushed", "on disk only"


@dataclass(frozen=True)
class FoundRun:
    run_id: str
    place: str  # ON_ORIGIN, COMMITTED or ON_DISK: the most public place it is in
    inputs: bytes | None  # its recorded `inputs.json`


class DecidedRuns(ABC):
    @abstractmethod
    def find(self, day: date) -> list[FoundRun]:
        """The book's runs of the day wherever they are, by run ID; `CommitFailed` when origin cannot be read."""


class GitDecidedRuns(DecidedRuns):
    def __init__(self, git: Git, book: str):
        self.git, self.store = git, DecisionStore(git.root, book)

    def find(self, day: date) -> list[FoundRun]:
        folder = self.store.day_folder(day)
        name = folder.relative_to(self.git.root).as_posix()
        try:
            self.git("fetch", "-q", "origin", self.git.target)
            origin, head = f"origin/{self.git.target}", "HEAD"
            places = {ON_ORIGIN: self._runs(origin, name), COMMITTED: self._runs(head, name)}
        except GitError as failed:
            raise CommitFailed(f"origin could not be checked for an earlier decision: {failed}") from failed
        places[ON_DISK] = {run.name for run in self.store.runs(day)}
        found = []
        for run_id in sorted(set().union(*places.values())):
            place = next(p for p in (ON_ORIGIN, COMMITTED, ON_DISK) if run_id in places[p])
            commit = origin if place == ON_ORIGIN else head
            inputs = folder / run_id / INPUTS_FILE
            data = inputs.read_bytes() if inputs.is_file() else self.git.show(commit, f"{name}/{run_id}/{INPUTS_FILE}")
            found.append(FoundRun(run_id, place, data))
        return found

    def _runs(self, commit: str, folder: str) -> set[str]:
        listed = self.git("ls-tree", "-d", "--name-only", f"{commit}:{folder}", check=False)
        return {n for n in listed.stdout.split() if not n.startswith(".")} if listed.returncode == 0 else set()


def changed_fields(recorded: bytes | None, fresh: bytes) -> list[str]:
    """The top-level fields of `inputs.json` that differ, byte for byte as `DecisionRun` writes them; [] when equal."""
    if recorded == fresh:
        return []
    if recorded is None:
        return ["(no recorded inputs)"]
    old, new = json.loads(recorded), json.loads(fresh)
    return sorted(key for key in set(old) | set(new) if old.get(key) != new.get(key))
