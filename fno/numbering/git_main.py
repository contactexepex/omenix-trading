"""The git side of a number claim (story O12): a temporary worktree of `origin/main`, one commit, one push.

The caller's branch, index and working files are never touched (only its `origin/main` ref is refreshed); the
worktree is removed afterwards, whether the claim worked or not.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from fno.numbering.categories import Category
from fno.numbering.numbered_items import numbered_items
from fno.numbering.registry import read_rows

REMOTE = "origin"
BRANCH = "main"
TRACKING = f"refs/remotes/{REMOTE}/{BRANCH}"
FETCH_MAIN = ("fetch", "-q", REMOTE, f"+refs/heads/{BRANCH}:{TRACKING}")
# What git prints when someone else's push came first: `main` moved since the copy was made, or both pushes reached
# the server together and the other one updated the ref first.
RACE_LOST = ("[rejected]", "non-fast-forward", "fetch first", "cannot lock ref", "failed to update ref")


class GitFailed(RuntimeError):
    """A git step failed for a reason other than a lost race (no network, no remote, a refused commit): the claim
    stops. `output` is everything git printed (a hook's own stdout reaches it through git's stderr), shown in full
    before the claim's one-line verdict."""

    def __init__(self, step: str, output: str):
        super().__init__(f"git {step} failed: {output}")
        self.step, self.output = step, output


def _git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    done = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if check and done.returncode != 0:
        raise GitFailed(args[0], _printed(done))
    return done


def _printed(done: subprocess.CompletedProcess) -> str:
    return "\n".join(part.strip() for part in (done.stdout, done.stderr) if part.strip())


class MainCopy:
    """A detached worktree at the latest `main`, where a registry row is committed and pushed."""

    def __init__(self, path: Path):
        self.path = path

    def taken(self, category: Category) -> set[str]:
        """Every number this copy of `main` holds in the category: registry rows and files (or headings)."""
        rows = {row.number for row in read_rows(self.path / category.registry)}
        return rows | {item.number for item in numbered_items(self.path, category)}

    def commit_and_push(self, registry: str, message: str) -> bool:
        """True when `main` accepted the push; False when someone pushed first (the race is lost, retry). Any other
        refusal (no access, a protected branch, no network, a server hook) raises GitFailed with git's own words."""
        _git(self.path, "add", "--", registry)
        _git(self.path, "commit", "-q", "-m", message, "--", registry)
        pushed = _git(self.path, "push", REMOTE, f"HEAD:refs/heads/{BRANCH}", check=False)
        if pushed.returncode == 0:
            return True
        if any(sign in pushed.stderr for sign in RACE_LOST):
            return False
        raise GitFailed("push", _printed(pushed))

    def reset_to_main(self) -> None:
        _git(self.path, *FETCH_MAIN)
        _git(self.path, "reset", "-q", "--hard", TRACKING)


class GitMain:
    """The repository whose `origin` holds the `main` that numbers are claimed on."""

    def __init__(self, repository: Path):
        self._repository = repository

    @contextmanager
    def main_copy(self) -> Iterator[MainCopy]:
        _git(self._repository, *FETCH_MAIN)
        place = Path(tempfile.mkdtemp(prefix="number-claim-"))
        try:
            _git(self._repository, "worktree", "add", "-q", "--detach", str(place), TRACKING)
            yield MainCopy(place)
        finally:
            _git(self._repository, "worktree", "remove", "--force", str(place), check=False)
            shutil.rmtree(place, ignore_errors=True)
            _git(self._repository, "worktree", "prune", check=False)
