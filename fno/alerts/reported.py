"""The daily run's alerts (story O1): every alert of the run, O1's and the desk's, goes through one sender that prints
any alert Slack did not take ("alert NOT sent: <reason> | <text>"), so the routine posts those lines with the Slack
connector (CLAUDE.md's 3 pm rules). An alert is never lost silently when Slack is down or the token is missing."""

from __future__ import annotations

from collections.abc import Callable

from ..alerts.sender import SENT, AlertSender

UNSENT_LINE = "{outcome} | {text}"


class ReportedAlerts(AlertSender):
    def __init__(self, sender: AlertSender, out: Callable[[str], None] = print):
        self.sender, self.out = sender, out

    def send(self, text: str) -> str:
        outcome = self.sender.send(text)
        if outcome != SENT:
            self.out(UNSENT_LINE.format(outcome=outcome, text=text))
        return outcome
