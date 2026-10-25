"""The repository questions the collector asks (stories F1 and G5): on top of the research ledger's `Git`, which
commit first added a file. A book's commitment counts as first published; a later rewrite of the file never changes
its receipt."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ..research_engine.ledger import Git


@dataclass(frozen=True)
class RepoHistory(Git):
    def first_commit_adding(self, path: str) -> str | None:
        found = self._out("log", "--format=%H", "--reverse", "--diff-filter=A", "--", path).split()
        return found[0] if found else None

    def committed_at(self, commit: str) -> datetime:
        """The commit's own committer date: set by whoever made it, so only ever a bound to search from."""
        return datetime.fromisoformat(self._out("show", "-s", "--format=%cI", commit).strip())
