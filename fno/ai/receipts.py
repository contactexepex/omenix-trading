"""When a book's file reached the repository, by GitHub's clock (story F1's receipt time). `PushReceipts` is the
interface; `GitHubActivityReceipts` reads the repository's activity log (`ActivityLog`), where GitHub records each push
to `main` with its server timestamp and the commits before and after it. A commit's receipt is the push whose `after`
contains it and whose `before` does not. A commit's own date is set by whoever made it and is never the receipt; it
only says how far back to search (story receipts-reach), so a date set later than the real push finds no push and
fails closed. Anything unclear raises `ReceiptUnknown`, which the collector treats as late (fails closed)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import datetime, timedelta

from .activity_log import ActivityLog, ReceiptAccessDenied, ReceiptUnavailable, ReceiptUnknown
from .history import RepoHistory

__all__ = ["GitHubActivityReceipts", "PushReceipts", "ReceiptAccessDenied", "ReceiptNotFound", "ReceiptOutsideLog",
           "ReceiptUnavailable", "ReceiptUnknown"]  # fmt: skip
NO_COMMIT = "0" * 40
CLOCK_MARGIN = timedelta(days=1)  # a committer's clock ahead of GitHub's still finds its push
NOT_FOUND = "no push of {commit} in GitHub's activity log of main since {since} ({pages} pages read)"
NOT_MONOTONIC = "GitHub's activity log of main is not one fast-forward line at {at}: no receipt for {commit}"
PLAIN_PUSH = "push"  # activity_type of a fast-forward push; a force_push can drop commits from main
OUTSIDE = "GitHub's activity log ends at {oldest}, before {commit} could be pushed (from {since}; {pages} pages read)"


class ReceiptNotFound(ReceiptUnknown):
    """The log covers every moment the commit could have been pushed, and holds no push of it: a real answer."""


class ReceiptOutsideLog(ReceiptUnknown):
    """The log no longer reaches back to when the commit could have been pushed: the push time cannot be known."""


class PushReceipts(ABC):
    @abstractmethod
    def received_at(self, commit: str) -> datetime:
        """GitHub's time of the push that first brought `commit` to `main`, or ReceiptUnknown."""


class GitHubActivityReceipts(PushReceipts):
    def __init__(self, repository: str, token: str, history: RepoHistory, get: Callable | None = None):
        self._history, self._log = history, ActivityLog(repository, token, get)

    @property
    def pages(self) -> int:
        """Pages of the log read so far by this reader (each question reads only the pages it still needs)."""
        return self._log.pages

    def received_at(self, commit: str) -> datetime:
        since = self._history.committed_at(commit) - CLOCK_MARGIN
        push = self._first_bringing(commit, self._log.since(since))
        if push is not None:
            return datetime.fromisoformat(push["timestamp"])
        fields = {"commit": commit[:10], "since": since.isoformat(), "pages": self._log.pages}
        if self._log.ended and self._log.oldest is not None and self._log.oldest > since:
            raise ReceiptOutsideLog(OUTSIDE.format(oldest=self._log.oldest.isoformat(), **fields))
        raise ReceiptNotFound(NOT_FOUND.format(**fields))

    def _first_bringing(self, commit: str, pushes: list[dict]) -> dict | None:
        """The first push (oldest first) whose `after` holds the commit and whose `before` does not. On plain pushes,
        each a fast-forward of main, "holds it" turns true once and stays true, so the push is found by halving (about
        11 ancestry checks for 1,900 pushes, story receipt-bisect) and then checked exactly; a window with any other
        kind of activity (a force push) is read push by push."""
        if any(push.get("activity_type") != PLAIN_PUSH for push in pushes):
            return next((push for push in pushes if self._brings(commit, push)), None)
        low, high = 0, len(pushes)
        while low < high:
            middle = (low + high) // 2
            if self._history.is_ancestor(commit, pushes[middle].get("after") or ""):
                high = middle
            else:
                low = middle + 1
        if low == len(pushes):
            return None
        if self._brings(commit, pushes[low]):
            return pushes[low]
        if low == 0:  # already held before the window: pushed before the commit's own date (a date set later)
            return None
        raise ReceiptUnknown(NOT_MONOTONIC.format(commit=commit[:10], at=pushes[low]["timestamp"]))

    def _brings(self, commit: str, push: dict) -> bool:
        before, after = push.get("before") or NO_COMMIT, push.get("after") or ""
        new = before == NO_COMMIT or not self._history.is_ancestor(commit, before)
        return new and self._history.is_ancestor(commit, after)
