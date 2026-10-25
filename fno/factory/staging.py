"""The git questions registration asks (story R1): D1's history adapter plus what is staged for the next commit."""

from __future__ import annotations

from ..playbook.history import PlaybookGit


class FactoryGit(PlaybookGit):
    def staged_paths(self) -> list[str]:
        return self._out("diff", "--cached", "--name-only").split()
