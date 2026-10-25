"""The rehearsal's own checkout (story REH1): a local clone of the checkout it starts from, with today's code and its
data folders as they were on `main` just before the routine's start on the replayed day (only the paths today's main
still tracks: REH1e). Its `origin` is a local bare repository, so every committer of every step pushes `HEAD:main`
exactly as in a real run without reaching GitHub.
The one push to GitHub is `publish`: the bare `main` to `refs/heads/rehearsal/<day>-<run_id>`, checked before git
runs. The record scan runs on every commit (the clone's hooks path is set and checked)."""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Sequence
from datetime import datetime
from pathlib import Path

from .mode import BRANCH_PREFIX, Rehearsal

DATA_FOLDERS = ("journal", "receipts", "research/data", "research/forecasts", "research/ops")
HOOKS_PATH = ".githooks"
REFS_PREFIX = f"refs/heads/{BRANCH_PREFIX}"
RECORD_MAIN = "origin/main"  # the source checkout's view of main: the real record
DATA_AS_OF = "Rehearsal {day} {run_id}: data as of {at}"
NOT_A_REHEARSAL_REF = "rehearsal: refused to push {ref}: only refs/heads/rehearsal/... may be pushed"
NO_HOOKS = "rehearsal: the clone's core.hooksPath is {found!r}, not .githooks: the record scan would not run"
NO_COMMIT_BEFORE = "rehearsal: main has no commit before {at}"


class RehearsalCheckoutError(RuntimeError):
    """The rehearsal's checkout could not be made or published; nothing ran and nothing reached GitHub."""


def run_git(cwd: Path, *args: str) -> str:
    done = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=False)
    if done.returncode != 0:
        raise RehearsalCheckoutError(f"git {' '.join(args[:2])} failed: {(done.stderr or done.stdout).strip()[-300:]}")
    return done.stdout


class RehearsalCheckout:
    def __init__(self, source: Path, rehearsal: Rehearsal, home: Path, git: Callable[..., str] = run_git,
                 data_folders: Sequence[str] = DATA_FOLDERS):  # fmt: skip
        self.source, self.rehearsal, self.git, self.data_folders = Path(source), rehearsal, git, data_folders
        self.root = Path(home) / rehearsal.run_id
        self.clone, self.bare = self.root / "checkout", self.root / "origin.git"

    def create(self, start: datetime) -> str:
        """The clone (the source's committed code), its data as of `start` on the source's `origin/main`, one data
        commit, and the local bare origin holding it as `main`; the data commit's ID."""
        if self.git(self.source, "rev-parse", "--is-shallow-repository").strip() == "true":
            self.git(self.source, "fetch", "-q", "--unshallow", "origin")  # the day's history, and a whole clone
        before = self.git(self.source, "rev-list", "-1", f"--before={start.isoformat()}", RECORD_MAIN).strip()
        if not before:
            raise RehearsalCheckoutError(NO_COMMIT_BEFORE.format(at=start.isoformat()))
        self.root.mkdir(parents=True, exist_ok=True)
        self.git(self.root, "clone", "-q", "--no-local", str(self.source), str(self.clone))
        self.git(self.clone, "config", "core.hooksPath", HOOKS_PATH)
        self.check_hooks()
        self.git(self.clone, "fetch", "-q", str(self.source), before)
        present = [f for f in self.data_folders if (self.clone / f).exists()]
        self.git(self.clone, "restore", f"--source={before}", "--staged", "--worktree", "--", *present)
        self._drop_moved_since(before, present)
        message = DATA_AS_OF.format(day=self.rehearsal.day, run_id=self.rehearsal.run_id, at=start.isoformat())
        self.git(self.clone, "commit", "-q", "--allow-empty", "-m", message)  # the hooks run: never --no-verify
        self.git(self.root, "init", "-q", "--bare", "-b", "main", str(self.bare))
        self._install_push_log()
        self.git(self.clone, "push", "-q", str(self.bare), "HEAD:refs/heads/main")
        self.git(self.clone, "remote", "set-url", "origin", str(self.bare))
        self.git(self.clone, "fetch", "-q", "origin")
        return self.git(self.clone, "rev-parse", "HEAD").strip()

    def _drop_moved_since(self, before: str, folders: Sequence[str]) -> None:
        """A file the day had that today's main no longer tracks (moved to Drive since, as O9b's VIX files on 23 Oct)
        stays out: its data comes from Drive through the recorded sources, and today's record scan rightly refuses it
        as a repository file (REH1e, DRY2's stop). The scan is never bypassed."""
        moved = sorted(set(self._tracked(before, folders)) - set(self._tracked("HEAD", folders)))
        if moved:
            self.git(self.clone, "rm", "-q", "-f", "--", *moved)

    def _tracked(self, commit: str, folders: Sequence[str]) -> list[str]:
        return self.git(self.clone, "ls-tree", "-r", "--name-only", commit, "--", *folders).splitlines()

    def _install_push_log(self) -> None:
        """The bare origin logs each push to main with the replay time, for the rehearsal's push receipts (REH1b)."""
        from .push_receipts import post_receive_hook

        self.rehearsal.state.mkdir(parents=True, exist_ok=True)
        hook = self.bare / "hooks" / "post-receive"
        hook.write_text(post_receive_hook(self.rehearsal.state), encoding="utf-8")
        hook.chmod(0o755)

    def check_hooks(self) -> None:
        found = self.git(self.clone, "config", "--get", "core.hooksPath").strip()
        if found != HOOKS_PATH:
            raise RehearsalCheckoutError(NO_HOOKS.format(found=found))

    def publish(self, remote: str) -> str:
        """The bare `main` to GitHub as the rehearsal's branch, and nothing else; the ref pushed."""
        ref = f"refs/heads/{self.rehearsal.branch}"
        refuse_unless_rehearsal_ref(ref)
        self.git(self.bare, "push", "-q", remote, f"refs/heads/main:{ref}")
        return ref


def refuse_unless_rehearsal_ref(ref: str) -> None:
    if not ref.startswith(REFS_PREFIX) or ".." in ref or ref.endswith("/"):
        raise RehearsalCheckoutError(NOT_A_REHEARSAL_REF.format(ref=ref))
