"""How a command prints its #fno-desk alerts (O2's outage days; the 3 pm quotes, A16's recorder, A12's archive). The
command's sender is O1's `ReportedAlerts`, wired where the command builds its sender: it prints an alert Slack did not
take as "alert NOT sent: <reason> | <text>", so the routine can post the text itself. The command prints only a sent
alert's outcome, never a bare "alert NOT sent" line without its text."""

from __future__ import annotations

from .sender import SENT, AlertSender


def announce(alerts: AlertSender, text: str) -> None:
    outcome = alerts.send(text)
    if outcome == SENT:
        print(outcome)
