"""The transcript's check of a decision session's model fields (story F1t criterion 3c, revision 2): the session copies
`last_served_model` and `session_context.model` from its session tool into its answer, so the auditor who reads the
transcript (the same sessions as the transcript audit) records whether the copied fields equal the tool's answer. A
difference is a breach, `model_misreported`, counted by the decision stop rule beside the transcript breaches. It is
F1t's own record because the transcript audit's breach kinds are frozen with protocol v4 (`fno/ai/transcript_audit.py`
is hashed by `FREEZE_v4.md`), and the forecasts never copy those fields."""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import date, datetime
from pathlib import Path

from ..ai.run_terms import RunTerms
from ..ai.stop_rule import BREACHES_TO_STOP, WINDOW_SESSION_DAYS, breached_days
from .paths import model_audit_path

MATCH, MISREPORTED = "match", "model_misreported"
RESULTS = (MATCH, MISREPORTED)
STOPPED = "stopped: {count} breaches (transcript or model fields) in {window} decision days ({days}); register a fixed "
STOPPED += "version"


class ModelAuditRefused(ValueError):
    """A malformed record, or one already written for that book-day (written once)."""


class ModelAudits:
    def __init__(self, root: Path):
        self.root = Path(root)

    def get(self, day: date, book: str) -> dict | None:
        path = self.root / model_audit_path(day, book)
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None

    def record(self, day: date, book: str, version: str, result: str, evidence: str, auditor: str,
               now: datetime) -> str:  # fmt: skip
        if result not in RESULTS:
            raise ModelAuditRefused(f"result must be one of {', '.join(RESULTS)}, not {result!r}")
        if not (version and evidence.strip() and auditor.strip()):
            raise ModelAuditRefused("a model audit needs the fired version, its evidence and its auditor")
        path = self.root / model_audit_path(day, book)
        if path.is_file():
            raise ModelAuditRefused(f"{path.relative_to(self.root)} already exists (written once)")
        record = {"book": book, "day": day.isoformat(), "version": version, "result": result, "evidence": evidence,
                  "auditor": auditor, "recorded_at": now.isoformat()}  # fmt: skip
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, sort_keys=True, indent=1) + "\n", encoding="utf-8")
        return str(path.relative_to(self.root))


def decision_stop_reason(root: Path, book: str, version: str, day: date, terms: RunTerms,
                         sessions: Sequence[date]) -> str:  # fmt: skip
    """Why the book's decision routine must not be fired on `day`, or '': the forecasts' stop rule (two breaches in
    the last 20 session days, under this version), where a breach is a transcript breach or a misreported model."""
    window = [d for d in sorted(sessions) if d < day][-WINDOW_SESSION_DAYS:]
    audits = ModelAudits(root)
    misreported = [d for d in window if (a := audits.get(d, book)) and a["result"] == MISREPORTED
                   and a["version"] == version]  # fmt: skip
    days = sorted(set(breached_days(root, book, version, day, terms, sessions)) | set(misreported))
    if len(days) < BREACHES_TO_STOP:
        return ""
    listed = ", ".join(d.isoformat() for d in days)
    return STOPPED.format(count=len(days), window=WINDOW_SESSION_DAYS, days=listed)
