"""A22's morning capture (agreed with O8's owner, 21 Oct): the day row's receipt pushed to GitHub by A22's
`PREOPEN_RECEIPT_BY`. Judged by the receipt's push time, never a time the routine wrote itself; no receipt means
the routine never ran or never pushed (a routine that never starts is noticed here, that evening)."""

from __future__ import annotations

from datetime import date, datetime

from ..preopen.day_row import receipt_path
from .evidence import Evidence
from .model import CheckResult, Deadline, SessionCheck, absent, judged


class PreopenCheck(SessionCheck):
    def __init__(self, evidence: Evidence, deadline: Deadline):
        self.evidence, self.deadline = evidence, deadline

    def check(self, session: date, now: datetime) -> CheckResult:
        receipt = receipt_path(session)
        if self.evidence.text(receipt) is None:
            return absent(now, self.deadline.on(session), "never ran: no pre-open day row receipt")
        return judged(self.evidence.file_pushed_at(receipt), self.deadline.on(session), "pushed")
