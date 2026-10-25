"""Is the code running now the code a record was made with (judge 80)? A replay is a reproduction only when the
working tree's `fno/` and `config.yaml` equal those of the record's `code_commit`, uncommitted and untracked files
included. Otherwise it is refused, naming the commit to replay in a worktree of (`git worktree add <dir> <commit>`)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from .history import PlaybookGit

DECISION_CODE = ("fno", "config.yaml")  # what a decision's result depends on


class CodeTree(Protocol):
    def matches(self, commit: str) -> bool: ...


class GitCodeTree:
    def __init__(self, git: PlaybookGit, paths: Sequence[str] = DECISION_CODE):
        self.git, self.paths = git, tuple(paths)

    def matches(self, commit: str) -> bool:
        return self.git.tree_matches(commit, self.paths)
