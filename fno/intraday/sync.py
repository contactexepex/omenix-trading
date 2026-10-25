"""The recorder's link to the repository (story A16): pull before settling marks, so a run sees the rows the other
overlapping run pushed, and commit after each mark. Two checkouts write one-file-per-record folders; a same-file clash
keeps the copy already on GitHub (the first push). Only the recorder's own paths are committed (A16e), and anything
else staged in the checkout stops both the pull and the commit, with one alert per run. A dry run uses `NoSync`:
nothing pulled, committed or pushed."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..alerts.sender import AlertSender
from ..storage.owned_paths_commit import OwnedPathsCommitter

PULLED = "pulled main"
NOT_PULLED = "pull failed, settling from this checkout as it is: {reason}"
NOT_PUBLISHED = "dry run: nothing pulled, committed or pushed"
FOREIGN_STAGED = "{label} NOT pulled or committed: {count} file(s) staged that are not the recorder's: {paths}"
SHOWN_PATHS = 5  # an alert names at most this many staged paths, then how many more


class LedgerSync(ABC):
    @abstractmethod
    def pull(self) -> str:
        """Brings in what other runs pushed; a one-line outcome (never raises)."""

    @abstractmethod
    def commit(self, what: str) -> str:
        """Commits and pushes this folder; a one-line outcome (never raises, never bypasses a hook)."""


class GitLedgerSync(LedgerSync):
    def __init__(self, committer: OwnedPathsCommitter, alerts: AlertSender):
        self.committer, self.alerts = committer, alerts
        self.alerted = False  # one alert per run (one process), never one per mark

    def pull(self) -> str:
        refused = self._foreign_staged()
        if refused:
            return refused
        pulled = self.committer.pull()
        if pulled.returncode == 0:
            return PULLED
        self.committer.abort_merge()
        text = (pulled.stderr or pulled.stdout or "").strip()
        return NOT_PULLED.format(reason=text.splitlines()[0] if text else f"exit code {pulled.returncode}")

    def commit(self, what: str) -> str:
        return self._foreign_staged() or self.committer.commit(what)

    def _foreign_staged(self) -> str:
        """The refusal line when another writer has staged anything (paths only, never contents); "" otherwise."""
        staged = self.committer.foreign_staged()
        if not staged:
            return ""
        more = f" and {len(staged) - SHOWN_PATHS} more" if len(staged) > SHOWN_PATHS else ""
        line = FOREIGN_STAGED.format(label=self.committer.label, count=len(staged),
                                     paths=", ".join(staged[:SHOWN_PATHS]) + more)  # fmt: skip
        if self.alerted:
            return line
        self.alerted = True
        return f"{line}; {self.alerts.send(line)}"


class NoSync(LedgerSync):
    def pull(self) -> str:
        return NOT_PUBLISHED

    def commit(self, what: str) -> str:
        return NOT_PUBLISHED
