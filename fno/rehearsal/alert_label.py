"""#fno-desk alerts in a rehearsal start with the label (story REH1), chosen by `build_alert_sender`."""

from __future__ import annotations

import os
from collections.abc import Mapping

from ..alerts.sender import AlertSender
from .mode import labelled, rehearsal


class LabelledAlerts(AlertSender):
    def __init__(self, inner: AlertSender, label: str):
        self.inner, self.label = inner, label

    def send(self, text: str) -> str:
        return self.inner.send(labelled(self.label, text))


def rehearsed_alerts(sender: AlertSender, env: Mapping[str, str] = os.environ) -> AlertSender:
    mode = rehearsal(env)
    return sender if mode is None else LabelledAlerts(sender, mode.label)
