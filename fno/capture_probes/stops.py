"""A source stopped for the day (story MS-P0b section 3): one plain line to #fno-desk through the existing
`AlertSender` and one O10 row in the capture-error log. The line names the source, the slot and the reason (a status,
a class name or the cap), never a value, a header, a cookie or a token."""

from __future__ import annotations

from datetime import date

from ..alerts.sender import AlertSender
from ..health.capture_errors import CaptureError, CaptureErrorLog
from .constants import CAP_LINE, CAPTURE_JOB, STOP_LINE

KIND_RATE, KIND_CAP, KIND_BLOCKED = "rate_limited", "cap_reached", "blocked"


def stop_kind(reason: str) -> str:
    if "429" in reason:
        return KIND_RATE
    return KIND_CAP if reason.startswith(CAP_LINE.split("(")[0]) else KIND_BLOCKED


class StopRecorder:
    def __init__(self, alerts: AlertSender, log: CaptureErrorLog | None):
        """`log`: None in a dry run (no O10 row)."""
        self.alerts, self.log = alerts, log

    def stopped(self, session: date, source: str, slot: str, reason: str) -> list[str]:
        """The stop line and the alert's outcome line."""
        line = STOP_LINE.format(source=source, slot=slot, reason=reason)
        if self.log is not None:
            self.log.append(CaptureError(session, CAPTURE_JOB, source, stop_kind(reason), line, ""))
        return [line, self.alerts.send(line)]
