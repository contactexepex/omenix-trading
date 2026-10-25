"""Pushing the probe's own records to `main` (story MS-P0b section 5): its receipts, its counts files and the O10 log
only, through A16e's owned-paths committer (pull with `--no-rebase`, push to `main`, record scan on)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from pathlib import Path

from ..storage.owned_paths_commit import OwnedPathsCommitter

NOT_COMMITTED_MARK = "NOT committed"


class RepoPathsCommitter(OwnedPathsCommitter):
    """Owned paths anywhere in the repository (given from its root), not inside one folder."""

    def __init__(self, repository: Path, owned: Sequence[str], **options):
        super().__init__(repository, repository, (), **options)
        self.owned = tuple(owned)


class Publisher(ABC):
    @abstractmethod
    def publish(self, what: str) -> str | None:
        """None once pushed (or nothing to push), else the committer's one-line reason."""


class GitPublisher(Publisher):
    def __init__(self, committer: RepoPathsCommitter):
        self.committer = committer

    def publish(self, what: str) -> str | None:
        result = self.committer.commit(what)
        return result if NOT_COMMITTED_MARK in result else None


class NoPublish(Publisher):
    """A dry run pushes nothing."""

    def publish(self, what: str) -> str | None:
        return None
