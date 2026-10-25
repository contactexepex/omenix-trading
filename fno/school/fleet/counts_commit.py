"""The run's single commit (story MS-P1j; Judge B's note on judge 507.5, judge 523): it adds and commits exactly the
session's named files, never a folder, so a stray file (a writer's `.<name>.part`) is never swept in. The names may sit
anywhere in the checkout: the counts, and the instructor's counts file and receipts, which its step wrote on the run's
own thread (one committer per run). O9's `GitManifestRecorder` does the git work (pull, push, the hook check).

A refusal is never silent (judge 507.13): `SessionFilesCommitter.commit` returns its line, which the run alerts and
exits 1 on. The run's earlier commits that never reached `main` are its own (`run_paths`: the counts folder and the
instructor's receipts), so they never block a later commit and go up with it, and a rerun with nothing new to commit
still pushes them: the rerun completes what a refused push left."""

from collections.abc import Sequence
from pathlib import Path

from ...storage.manifest_commit import NOT_COMMITTED, NOTHING_AS, TARGET_BRANCH, GitManifestRecorder

LABEL = "school session files"
REFUSED = NOT_COMMITTED.split("{step}")[0].format(label=LABEL)  # how every refused outcome begins


class NamedFiles(GitManifestRecorder):
    """Exactly `files` (repository-relative), those that exist or are tracked: Git refuses a whole `add` when one
    pathspec matches nothing."""

    def __init__(self, repository: Path, files: Sequence[str], message: str, run_paths: Sequence[str] = ()):
        super().__init__(repository, repository, message=message, label=LABEL, run_paths=run_paths)
        self.files = tuple(files)

    def owns(self, path: str) -> bool:
        return path in self.files

    def commit(self, what: str) -> str:
        outcome = super().commit(what)
        if outcome == NOTHING_AS.format(label=self.label) and self._unpushed():
            return self._publish(0)  # an earlier run committed them and its push was refused
        return outcome

    def _not_committed(self, step: str, reason: str) -> str:
        """As O9's line, naming the files to commit by hand rather than a folder (this committer's is the checkout)."""
        return f"{REFUSED}{step} failed: {reason}. Commit {', '.join(self.files)} by hand"

    def _unpushed(self) -> bool:
        """A named file committed here and not on `main` as last fetched."""
        changed = self._git("diff", "--name-only", f"origin/{TARGET_BRANCH}...HEAD", "--", *self.files)
        return changed.returncode == 0 and bool(changed.stdout.strip())

    def _paths(self) -> list[str]:
        listed = self._git("ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", *self.files)
        present = set(listed.stdout.split("\0"))
        return [name for name in self.files if name in present]


class SessionFilesCommitter:
    def __init__(self, repository: Path, message: str, run_paths: Sequence[str] = ()):
        """`run_paths`: the folder prefixes ("research/school/counts/") whose unpushed commits are this run's own."""
        self.repository, self.message, self.run_paths = Path(repository), message, tuple(run_paths)

    def commit(self, what: str, paths: Sequence[str]) -> str | None:
        """`paths`: repository-relative files. None when they are on `main`; the refused outcome's line otherwise."""
        outcome = NamedFiles(self.repository, paths, self.message, self.run_paths).commit(what)
        return outcome if outcome.startswith(REFUSED) else None
