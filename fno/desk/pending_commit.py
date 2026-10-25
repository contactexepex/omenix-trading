"""A commit the daily run could not finish is kept, never redone (story E2b, judge 118 addendum 4, decision 47).

Before every commit of the run, the paths, their SHA-256 and the message are written to a local marker
(`journal/runs/.pending_commit.json`, git-ignored); a commit that succeeds removes it. A failed commit stops the run
and leaves the marker, so the step's outputs stay exactly as they were made. The rerun's first act is `recover()`: it
commits those files as they are on disk, under the original message, and never re-runs what made them. A file missing
or changed since it was recorded stops the rerun with that named: it is never regenerated, since a later snapshot
could give other decisions or a second fill.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Sequence
from pathlib import Path

from ..constants import JOURNAL_FOLDER
from .daily_ports import CommitFailed, Committer, OwnCommit
from .run_log import RUNS_FOLDER

MARKER = ".pending_commit.json"
RECOVERED = " (committed on the rerun, as recorded)"
CHANGED = "the files of '{message}' changed since they were recorded ({paths}); they are never regenerated: {fix}"
CHANGED_FIX = "restore them as recorded or resolve by hand, then remove {marker}"


class PendingChanged(CommitFailed):
    """A pending commit's files are missing or changed: nothing is committed and nothing is regenerated."""


class PendingCommitter(Committer):
    def __init__(self, committer: Committer, root: Path, marker: str = MARKER):
        """`marker`: each command keeps its own (story E5b: Book 1's decision and the daily run may overlap)."""
        self.committer, self.root = committer, Path(root)
        self.marker = self.root / JOURNAL_FOLDER / RUNS_FOLDER / marker

    def commit(self, paths: Sequence[Path], message: str, own_unpushed: OwnCommit | None = None) -> str:
        """The run's `recover()` comes first (`DailyRun.run`), so no marker is ever left here when this writes one."""
        self._write({"message": message, "files": {self._name(p): _sha256(Path(p)) for p in paths}})
        commit = self.committer.commit(paths, message, own_unpushed)
        self.marker.unlink()
        return commit

    def recover(self) -> str:
        """Commits the pending commit's files exactly as recorded; the commit ID, or empty when nothing is pending."""
        pending = self._pending()
        if pending is None:
            return ""
        files = pending["files"]
        changed = [name for name, digest in files.items() if _sha256(self.root / name) != digest]
        if changed:
            fix = CHANGED_FIX.format(marker=self._name(self.marker))
            raise PendingChanged(CHANGED.format(message=pending["message"], paths=", ".join(changed), fix=fix))
        named = [self.root / name for name in files]
        own = OwnCommit(pending["message"], files)
        commit = self.committer.commit(named, pending["message"] + RECOVERED, own_unpushed=own)
        self.marker.unlink()
        return commit

    def _pending(self) -> dict | None:
        return json.loads(self.marker.read_text(encoding="utf-8")) if self.marker.is_file() else None

    def _write(self, body: dict) -> None:
        self.marker.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.marker.with_name(f"{self.marker.name}.tmp")
        temporary.write_text(json.dumps(body, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temporary, self.marker)

    def _name(self, path: Path) -> str:
        return Path(path).resolve().relative_to(self.root.resolve()).as_posix()


def _sha256(path: Path) -> str | None:
    """The file's SHA-256; None when it is not a file (a missing file must still be missing on the rerun)."""
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
