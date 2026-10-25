"""The 3 pm recorders (Groww, and NSE in the same 14:33 routine): the day's `.canonical` names a complete, in-window
snapshot and GitHub received it by the capture's last pull (`LATEST_START`). `none` and an incomplete snapshot are
misses; no canonical at all means the recorder never ran."""

from __future__ import annotations

from datetime import date, datetime

from ..constants import HEALTH_MISSED
from ..quotes.recorder import NONE_MARKER, QuoteSnapshotRecorder
from .evidence import Evidence
from .model import CheckResult, Deadline, EvidenceUnknown, SessionCheck, absent, judged

QUOTES_FOLDER = "research/data/quotes"


class CanonicalCheck(SessionCheck):
    def __init__(self, evidence: Evidence, dataset: str, deadline: Deadline):
        self.evidence, self.dataset, self.deadline = evidence, dataset, deadline

    def _path(self, session: date, name: str) -> str:
        return f"{QUOTES_FOLDER}/{QuoteSnapshotRecorder.path(session, name, self.dataset)}"

    def check(self, session: date, now: datetime) -> CheckResult:
        canonical = self._path(session, f"nifty_{session:%Y%m%d}.canonical")
        text = self.evidence.text(canonical)
        if text is None:
            return absent(now, self.deadline.on(session), "never ran: no canonical")
        snapshot = text.strip()
        if snapshot == NONE_MARKER:
            return CheckResult(HEALTH_MISSED, "none")
        sidecar = self.evidence.json(self._path(session, f"{snapshot}.meta.json"))
        if sidecar is None:
            raise EvidenceUnknown(f"{canonical} names {snapshot}, whose sidecar is not committed")
        if not (sidecar.get("complete") is True and sidecar.get("in_window") is True):
            return CheckResult(HEALTH_MISSED, f"incomplete ({snapshot})")
        return judged(self.evidence.file_pushed_at(canonical), self.deadline.on(session), "pushed")
