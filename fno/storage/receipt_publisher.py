"""Pushing a receipt to the remote, the second half of a seal (story 3.4): a seal exists only once the receipt of the
saved file is on `main`, so a fill can name a seal that others can see."""

import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol, runtime_checkable

from ..research_engine.ledger import Git
from .manifest_commit import TARGET_BRANCH, ManifestRecorder
from .receipts import Receipt, ReceiptFolder

COMMIT_FORMAT = "%H %cI"  # commit id, committer time (the pushed commit's own time is the seal's pushed_at)
NOT_ON_REMOTE = "the receipt of {path} is not on {target} ({outcome})"
PULL_FAILED = "the receipt of {path} was not pushed: main could not be pulled first"
SHALLOW = "this checkout is a shallow clone and could not be deepened: run git fetch --unshallow origin {target}"


class SealNotPushed(Exception):
    """The receipt could not be committed and pushed: the file has no seal and nothing may fill on it."""


class ShallowClone(SealNotPushed):
    """A shallow clone takes its boundary commit for the commit that added every file, so no seal can be named."""


@dataclass(frozen=True)
class PushedReceipt:
    commit: str
    pushed_at: datetime  # commit time, not push time; the proof is the remote receipt
    sha256: str  # the SHA-256 the receipt holds in that commit


@runtime_checkable
class ReceiptPublisher(Protocol):
    def publish(self, drive_path: str, what: str) -> PushedReceipt:
        """Commit and push the receipts, then name the commit on the remote that holds this file's receipt
        (`SealNotPushed` when there is none). Called again for a receipt already pushed, it names the same commit."""

    def published(self, drive_path: str) -> PushedReceipt | None:
        """The commit on the remote that added this file's receipt, with the SHA-256 it holds there, or None."""


class RemoteReceipts:
    """The receipts on the remote's `main`: `refresh` fetches it (and deepens a shallow clone); `find` only reads the
    history last fetched, so it writes nothing in the checkout and can run beside another git writer (judge 523)."""

    def __init__(self, receipts: ReceiptFolder, repository: Path, run=subprocess.run):
        self.receipts, self.repository, self.run = receipts, Path(repository), run

    def refresh(self) -> None:
        self._git("fetch", "origin", TARGET_BRANCH)
        self._deepen()

    def find(self, drive_path: str) -> PushedReceipt | None:
        """The commit on the fetched `main` that added this file's receipt, with the SHA-256 it holds there, or None."""
        file = self.receipts.file_for(drive_path).relative_to(self.repository).as_posix()
        added = self._git("log", f"origin/{TARGET_BRANCH}", "--diff-filter=A", "-1", f"--format={COMMIT_FORMAT}",
                          "--", file)  # fmt: skip
        if added.returncode != 0 or not added.stdout.strip():
            return None
        commit, when = added.stdout.split()
        text = self._git("show", f"{commit}:{file}")
        if text.returncode != 0:
            return None
        return PushedReceipt(commit, datetime.fromisoformat(when), Receipt.from_text(drive_path, text.stdout).sha256)

    def _deepen(self) -> None:
        """The add commit is found by history, which a shallow clone cuts short at its boundary commit (the routine and
        the CCR containers clone at depth 50): fetch the rest once, or refuse by name."""
        git = Git(self.repository)
        if git.is_shallow():
            self._git("fetch", "--unshallow", "origin", TARGET_BRANCH)
        if git.is_shallow():
            raise ShallowClone(SHALLOW.format(target=TARGET_BRANCH))

    def _git(self, *args: str) -> subprocess.CompletedProcess:
        return self.run(["git", *args], cwd=self.repository, capture_output=True, text=True)


class GitReceiptPublisher:
    def __init__(self, recorder: ManifestRecorder, receipts: ReceiptFolder, repository: Path, run=subprocess.run):
        self.recorder, self.receipts, self.repository, self.run = recorder, receipts, Path(repository), run
        self.remote = RemoteReceipts(receipts, repository, run)

    def publish(self, drive_path: str, what: str) -> PushedReceipt:
        outcome = self.recorder.commit(what)
        found = self.published(drive_path) or self._push_unpushed(drive_path)
        if found is None:
            raise SealNotPushed(NOT_ON_REMOTE.format(path=drive_path, target=TARGET_BRANCH, outcome=outcome))
        return found

    def published(self, drive_path: str) -> PushedReceipt | None:
        self.remote.refresh()
        return self.remote.find(drive_path)

    def _push_unpushed(self, drive_path: str) -> PushedReceipt | None:
        """A receipt committed by an earlier run whose push failed: nothing is pending, so push it now."""
        pulled = self.recorder.pull()
        if pulled.returncode != 0:  # e.g. the checkout carries other unpushed commits: never pushed to main
            self.recorder.abort_merge()
            raise SealNotPushed(pulled.stderr.strip() or PULL_FAILED.format(path=drive_path))
        self.run(["git", "push", "origin", f"HEAD:{TARGET_BRANCH}"], cwd=self.repository, capture_output=True,
                 text=True)  # fmt: skip
        return self.published(drive_path)
