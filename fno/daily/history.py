"""The whole git history before the day starts (story O1, asked by E8, judge 203 should-fix 1): a cloud routine's
checkout is shallow (50 commits), and every commit older than its boundary then reads as made at that boundary. E8's
availability seals and E3's committed decisions are dated by commit time, so the run fetches the full history first.
If that fails, one alert names it and the day goes on: E8's step refuses in a shallow checkout on its own (entries fail
closed, exits run), and stopping the whole day would lose the quotes and the exits too."""

from __future__ import annotations

from ..alerts.sender import AlertSender
from ..desk.git_sync import Git, GitError

SHALLOW = (
    "F&O daily run: the checkout is shallow and its full history could not be fetched ({reason}); commit-time dates "
    "older than the boundary are unknown (E8's step refuses, entries fail closed, exits run). Fix: rerun with network"
)


class WholeHistory:
    def __init__(self, git: Git, alerts: AlertSender):
        self.git, self.alerts = git, alerts

    def __call__(self) -> None:
        try:
            self.git.unshallow()
        except GitError as failure:
            self.alerts.send(SHALLOW.format(reason=failure))
