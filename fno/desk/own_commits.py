"""Story O1, gap G4 (judge 412 add. 3, judge 419): the daily run's own commits that it could not push yet. The run's one
`GitCommitter` remembers each commit it made as an `OwnCommit` (its message and each file's SHA-256) until a push
carries it, so the run's next commit accepts it, checked by content, instead of refusing it as a stray (decision 51).
A stranger's commit is still refused. The list is also kept in a git-ignored file, so a rerun in the same container
still knows its own commits; a new container's clone holds only what origin holds, so it has none.

Deliberately not covered: Book 1's own decision commit, made by its `desk book1` child process with its own committer.
Left unpushed, it stays a stray to the run's committer and stops the next commit, because E5b's stop protects the
decision's timing (judge 419)."""

from __future__ import annotations

import json
import os
from pathlib import Path

from .daily_ports import OwnCommit

# git-ignored (.gitignore), never committed; in its own folder, as every reader of `journal/runs/*.json` takes each file
# there for a dated run log
OWN_UNPUSHED_FILE = "journal/runs/.own/unpushed.json"


class OwnUnpushed:
    def __init__(self, path: Path | None = None):
        """`path`: where the list survives a crash of the run; None keeps it in memory only."""
        self.path = path
        self.commits: list[OwnCommit] = self._read()

    def remember(self, commit: OwnCommit) -> None:
        self.commits.append(commit)
        self._write()

    def pushed(self) -> None:
        """Every commit the run made has reached origin: nothing is left to accept."""
        if self.commits:
            self.commits = []
            self._write()

    def _read(self) -> list[OwnCommit]:
        if self.path is None or not self.path.is_file():
            return []
        return [OwnCommit(c["message"], c["files"]) for c in json.loads(self.path.read_text(encoding="utf-8"))]

    def _write(self) -> None:
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        body = [{"message": c.message, "files": dict(c.files)} for c in self.commits]
        temporary = self.path.with_name(f"{self.path.name}.tmp")
        temporary.write_text(json.dumps(body, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temporary, self.path)
