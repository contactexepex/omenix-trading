"""The card reads committed records only (story T1 criterion 5): `GitHeadRecords` reads a file's bytes as committed at
`HEAD`, so an edited or untracked file in the working tree can never reach a card."""

from __future__ import annotations

import subprocess
from abc import ABC, abstractmethod
from pathlib import Path


class CommittedRecords(ABC):
    @abstractmethod
    def read(self, path: str) -> bytes | None:
        """The committed bytes of a repository path, or None when it is not committed."""

    @abstractmethod
    def names(self, folder: str) -> list[str]:
        """The committed file names directly inside a folder, sorted ([] when there is none)."""


class GitHeadRecords(CommittedRecords):
    def __init__(self, root: Path, commit: str = "HEAD"):
        self.root, self.commit = Path(root), commit

    def _git(self, *args: str) -> subprocess.CompletedProcess:
        """A failed or missing git reads as "not committed", so every record is named missing, never invented."""
        try:
            return subprocess.run(["git", *args], cwd=self.root, capture_output=True)
        except OSError:
            return subprocess.CompletedProcess(args, 1, b"", b"")

    def read(self, path: str) -> bytes | None:
        shown = self._git("show", f"{self.commit}:{path}")
        return shown.stdout if shown.returncode == 0 else None

    def names(self, folder: str) -> list[str]:
        listed = self._git("ls-tree", "-z", "--name-only", self.commit, f"{folder.rstrip('/')}/")
        if listed.returncode != 0:
            return []
        return sorted(Path(name).name for name in listed.stdout.decode("utf-8").split("\0") if name)

    def code_commit(self) -> str:
        return self._git("rev-parse", self.commit).stdout.decode("utf-8").strip() or "unknown"


class DownloadedRecords(CommittedRecords):
    """Story E2c: the paper accounts as the shared download wrote them from Drive (git-ignored, never committed): the
    card's one read outside `HEAD`, since the accounts are no longer in the public record."""

    def __init__(self, root: Path):
        self.root = Path(root)

    def read(self, path: str) -> bytes | None:
        file = self.root / path
        return file.read_bytes() if file.is_file() else None

    def names(self, folder: str) -> list[str]:
        found = self.root / folder
        return sorted(p.name for p in found.iterdir()) if found.is_dir() else []
