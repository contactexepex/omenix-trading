"""A sender that sends nothing and says what it would have sent: for stories whose alerts are data until a later
routine wires the Slack sender (story BG1). It sits beside `NoAlertSender` on purpose: that one reports a missing token
as a failure, while a dry run is the intended outcome and keeps the texts it would have sent, so tests read them."""

from __future__ import annotations

from .sender import AlertSender

DRY_RUN = "dry run, nothing sent; would send: {text}"


class DryRunAlertSender(AlertSender):
    def __init__(self):
        self.would_send: list[str] = []

    def send(self, text: str) -> str:
        self.would_send.append(text)
        return DRY_RUN.format(text=text)
