"""Makes manifest rows durable (story A10 follow-up): rows written at save time live in the repository's working tree
until committed, and a fresh checkout without them would report the saved files as unfingerprinted. After every
librarian run the rows are committed and pushed; `data-coverage` reports any that are still uncommitted.

The commit runs the repository's hooks (the public-record scan, story O5): a refused commit is reported, never
bypassed (no `--no-verify`). The branch is pulled with `--no-rebase` before pushing (CLAUDE.md: others push to it too).
"""

from __future__ import annotations

import subprocess
from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path

PUSH_ATTEMPTS = 3
TARGET_BRANCH = "main"
OFF_MAIN = "the checkout carries changes not on {target} outside this writer's paths: {paths}"
COMMIT_MESSAGE = "Manifests: SHA-256 rows written at save time ({what})"
MANIFEST_LABEL = "manifest rows"
COMMITTED_AS, NOTHING_AS = "{label} committed and pushed ({count} file(s))", "{label}: nothing new to commit"
COMMITTED = COMMITTED_AS.format(label=MANIFEST_LABEL, count="{count}")
NOTHING = NOTHING_AS.format(label=MANIFEST_LABEL)
NOT_COMMITTED = "{label} NOT committed: {step} failed: {reason}. Commit {folder}/ by hand"
# the words that tell a failed commit from a pushed one and from "nothing new to commit", read from the template above
NOT_COMMITTED_MARK = NOT_COMMITTED.partition("{label}")[2].partition(":")[0]
COMMIT_FAILED_ALERT = (
    "Omenix F&O {what}: the manifest rows were NOT committed or pushed (the run log has the reason); "
    "the files are in Drive, commit the manifests by hand"
)
NO_HOOKS = "core.hooksPath is not set, so the public-record scan would not run (git config core.hooksPath .githooks)"


class ManifestRecorder(ABC):
    @abstractmethod
    def pending(self) -> list[str]:
        """Manifest files with rows not yet committed (empty when everything is committed)."""

    @abstractmethod
    def commit(self, what: str) -> str:
        """Commits and pushes the pending manifests; a one-line outcome (never raises, never bypasses a hook)."""


class GitManifestRecorder(ManifestRecorder):
    def __init__(self, repository: Path, folder: Path, run=subprocess.run, message: str = COMMIT_MESSAGE,
                 label: str = MANIFEST_LABEL, keep_remote_on_conflict: bool = False,
                 run_paths: Sequence[str] = ()):  # fmt: skip
        """`keep_remote_on_conflict`: a pull conflict is settled with the copy already pushed (`-X theirs`), for a
        folder of write-once records where the first push wins (story A16); off for manifests. `run_paths`: path
        prefixes another committer of the same run writes (the A16 run's claims and ledger, judge 247): their
        unpushed commits are this run's own, so they never block this push and go up with it."""
        self.repository, self.run, self.message, self.label = Path(repository), run, message, label
        self.run_paths = tuple(run_paths)
        self.merge_option = ("-X", "theirs") if keep_remote_on_conflict else ()
        self.folder = Path(folder).resolve().relative_to(self.repository.resolve()).as_posix()

    def _git(self, *args: str) -> subprocess.CompletedProcess:
        return self.run(["git", *args], cwd=self.repository, capture_output=True, text=True)

    def _paths(self) -> list[str]:
        """The pathspecs this committer adds and commits (a commit with pathspecs takes only those: `--only`)."""
        return [self.folder]

    def pending(self) -> list[str]:
        paths = self._paths()
        if not paths:  # no pathspec at all would mean the whole repository
            return []
        status = self._git("status", "--porcelain", "--untracked-files=all", "--", *paths)
        return sorted(line[3:] for line in status.stdout.splitlines() if line.strip())

    def commit(self, what: str) -> str:
        files = self.pending()
        if not files:
            return NOTHING_AS.format(label=self.label)
        if not self._git("config", "core.hooksPath").stdout.strip():
            return self._not_committed("hooks", NO_HOOKS)  # the scan is never skipped, so neither is it bypassed
        paths = self._paths()
        for step, args in (
            ("add", ("add", "--", *paths)),
            ("commit", ("commit", "-m", self.message.format(what=what), "--", *paths)),
        ):
            result = self._git(*args)
            if result.returncode != 0:
                return self._not_committed(step, _first_line(result))
        return self._publish(len(files))

    def publish(self) -> str:
        """Pulls and pushes what is already committed, adding nothing: an A16 claim whose first push failed is on
        GitHub only once this push lands (story GW1); "nothing new to commit" proves nothing about the remote."""
        return self._publish(0)

    def _publish(self, count: int) -> str:
        """Pulls and pushes; another session pushing in between is retried (PUSH_ATTEMPTS in all)."""
        for _ in range(PUSH_ATTEMPTS):
            pulled = self.pull()
            if pulled.returncode != 0:
                self.abort_merge()
                return self._not_committed("pull", _first_line(pulled))
            pushed = self._git("push", "origin", f"HEAD:{TARGET_BRANCH}")
            if pushed.returncode == 0:
                return COMMITTED_AS.format(label=self.label, count=count)
        return self._not_committed("push", _first_line(pushed))

    def _not_committed(self, step: str, reason: str) -> str:
        return NOT_COMMITTED.format(label=self.label, folder=self.folder, step=step, reason=reason)

    def pull(self) -> subprocess.CompletedProcess:
        """Merges main whatever branch is checked out: a routine container starts on a session branch that GitHub
        does not have, and data belongs on main. Refused while the checkout carries anything else not on main, so
        unjudged work on a story branch never reaches main through a data push."""
        fetched = self._git("fetch", "origin", TARGET_BRANCH)
        if fetched.returncode != 0:
            return fetched
        changed = self._git("diff", "--name-only", f"origin/{TARGET_BRANCH}...HEAD")
        if changed.returncode != 0:
            return changed
        foreign = sorted(path for path in changed.stdout.splitlines() if path and not self._of_this_run(path))
        if foreign:
            reason = OFF_MAIN.format(target=TARGET_BRANCH, paths=", ".join(foreign))
            return subprocess.CompletedProcess(changed.args, 1, stdout="", stderr=reason)
        return self._git("pull", "--no-rebase", "--no-edit", *self.merge_option, "origin", TARGET_BRANCH)

    def owns(self, path: str) -> bool:
        return path.startswith(f"{self.folder}/")

    def _of_this_run(self, path: str) -> bool:
        return self.owns(path) or path.startswith(self.run_paths)

    def abort_merge(self) -> None:
        """Never leaves the checkout mid-merge: every later commit would fail."""
        self._git("merge", "--abort")


def _first_line(result: subprocess.CompletedProcess) -> str:
    text = (result.stderr or result.stdout or "").strip()
    return text.splitlines()[0] if text else f"exit code {result.returncode}"


def commit_failed(line: str) -> bool:
    """True for the committer's "NOT committed" line; False for "committed and pushed" and "nothing new to commit"."""
    return NOT_COMMITTED_MARK in line


def exit_for_commit(lines: Iterable[str], code: int, send_alert: Callable[[str], object], what: str) -> int:
    """The exit code a command ends with once its manifest commit has run: unchanged when the commit worked or had
    nothing to do; at least 1, with exactly one #fno-desk alert (codes only, no row), when any line says the
    rows were NOT committed. Rows that never reached GitHub are lost with the runner, so a green run with a
    failed commit is a silent failure."""
    if not any(commit_failed(line) for line in lines):
        return code
    send_alert(COMMIT_FAILED_ALERT.format(what=what))
    return max(code, 1)
