"""The git questions the playbook asks (story D1): B4's `Git` adapter plus the commits that changed one file."""

from __future__ import annotations

from typing import Protocol

from ..constants import PUBLISH_BRANCH
from ..research_engine.ledger import FILE_NOT_THERE, Git


class History(Protocol):
    def commit_exists(self, commit: str) -> bool: ...

    def is_ancestor(self, older: str, newer: str) -> bool: ...

    def committed_text(self, path: str, commit: str = "HEAD") -> str | None: ...

    def head(self) -> str: ...


class PlaybookGit(Git):
    """Every question gets git's real answer or raises `GitFailed` (B4's adapter); `commits_touching` is B4's."""

    def file_versions(self, path: str) -> list[str]:
        """The committed texts of `path`, oldest first."""
        texts = (self.committed_text(path, commit) for commit in self.commits_touching(path))
        return [text for text in texts if text is not None]

    def committed_bytes(self, path: str, commit: str) -> bytes | None:
        """The file's exact bytes at `commit` (None if not committed there)."""
        done = self._found("show", f"{commit}:{path}", not_there=FILE_NOT_THERE, text=False)
        return None if done is None else done.stdout

    def added_at(self, path: str) -> str | None:
        """The committer time (ISO, with offset) of the first commit that added `path`; None if it is not committed."""
        found = self._out("log", "--diff-filter=A", "--format=%cI", "--reverse", "--", path).split()
        return found[0] if found else None

    def added_in(self, path: str) -> tuple[str, str] | None:
        """(commit ID, committer time) of the first commit that added `path`; None if it is not committed."""
        found = self._out("log", "--diff-filter=A", "--format=%H %cI", "--reverse", "--", path).splitlines()
        if not found:
            return None
        commit, moment = found[0].split()
        return commit, moment

    def observed(self) -> str:
        """Pulls main (every run publishes there, whatever the checkout's branch) and returns the commit now checked
        out: what a reader at this moment can see. A refused pull raises: the stale checkout is not what a reader
        sees."""
        self._out("pull", "-q", "--no-rebase", "--no-edit", "origin", PUBLISH_BRANCH)
        return self.head()

    def tree_matches(self, commit: str, paths: tuple[str, ...]) -> bool:
        """True when `paths` in the working tree (uncommitted and untracked files included) equal them at `commit`."""
        if not self.commit_exists(commit):
            return False
        changed = not self._yes("diff", "--quiet", commit, "--", *paths)
        untracked = self._out("ls-files", "--others", "--exclude-standard", "--", *paths).strip()
        return not changed and not untracked
