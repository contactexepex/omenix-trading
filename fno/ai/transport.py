"""How a book's routine publishes its commitment and reveal (stories F1 and G5). `SubmissionTransport` is the
interface; `GitMainTransport` commits one file and pushes it to `main` (the path the 3 pm recorder routine already
uses), pulling and retrying when another push got there first. The commit goes through the repository's hooks (the
public-record scan, story O5); `--no-verify` is never used."""

from __future__ import annotations

import subprocess
from abc import ABC, abstractmethod
from pathlib import Path

PUSH_ATTEMPTS = 3
BRANCH = "main"


class PublishFailed(RuntimeError):
    """The file could not be committed or pushed; the message says which step."""


class SubmissionTransport(ABC):
    @abstractmethod
    def existing(self, path: str) -> str | None:
        """The file's text as published, or None."""

    @abstractmethod
    def publish(self, path: str, text: str, message: str) -> str:
        """Publishes the file once; returns the commit that holds it."""


class GitMainTransport(SubmissionTransport):
    def __init__(self, root: Path):
        self.root = Path(root)

    def existing(self, path: str) -> str | None:
        self._git("pull", "-q", "--no-rebase", "--no-edit", "origin", BRANCH)
        file = self.root / path
        return file.read_text(encoding="utf-8") if file.is_file() else None

    def publish(self, path: str, text: str, message: str) -> str:
        file = self.root / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(text, encoding="utf-8")
        self._git("add", path)
        self._git("commit", "-q", "-m", message)
        commit = self._git("rev-parse", "HEAD").strip()
        for attempt in range(PUSH_ATTEMPTS):
            if self._run("push", "-q", "origin", f"HEAD:{BRANCH}").returncode == 0:
                return commit
            if attempt + 1 < PUSH_ATTEMPTS:
                self._git("pull", "-q", "--no-rebase", "--no-edit", "origin", BRANCH)
        raise PublishFailed(f"git push of {path} failed {PUSH_ATTEMPTS} times")

    def _run(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(["git", *args], cwd=self.root, capture_output=True, text=True)

    def _git(self, *args: str) -> str:
        done = self._run(*args)
        if done.returncode != 0:
            raise PublishFailed(f"git {args[0]} failed: {(done.stderr or done.stdout).strip()[-300:]}")
        return done.stdout
