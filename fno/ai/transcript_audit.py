"""The transcript audit of an AI book's routine session (owner's condition 1, 14 Oct 2026): one record per book-day,
written once, saying who read which session, when, and whether it broke an isolation rule. A breach is any of
`BREACH_KINDS`; a breached day is never scored, and two breaches in 20 session days stop that book's fires until a new
version is registered (`fno/ai/stop_rule.py`)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path

from .run_terms import V2_TERMS, RunTerms

CLEAN, BREACH = "clean", "breach"
BREACH_KINDS = (
    "file_outside_input",  # opened a repository file other than what `brief` printed
    "network_beyond_pushes",  # used the network for anything but the commitment and reveal pushes
    "ran_forecast_code",  # ran `fno.forecast` code (it computes the rule books' answers)
    "read_other_records",  # read `research/forecasts/` (other books' records or submissions)
)


class AuditRefused(ValueError):
    """The audit record is malformed, or one already exists for that book-day (written once)."""


@dataclass(frozen=True)
class TranscriptAudit:
    book: str
    day: str
    version: str  # the version label the day was fired with
    session: str  # the routine session read
    result: str  # clean or breach
    breaches: list[str] = field(default_factory=list)  # kinds from BREACH_KINDS
    evidence: str = ""  # what was seen (tool call, file, time), never a secret
    auditor: str = ""
    audited_at: str = ""

    def __post_init__(self):
        if self.result not in (CLEAN, BREACH):
            raise AuditRefused(f"result must be {CLEAN} or {BREACH}, not {self.result!r}")
        if (self.result == BREACH) != bool(self.breaches):
            raise AuditRefused("a breach names at least one kind; a clean audit names none")
        unknown = [k for k in self.breaches if k not in BREACH_KINDS]
        if unknown:
            raise AuditRefused(f"unknown breach kinds {unknown}; known: {', '.join(BREACH_KINDS)}")
        if not (self.session and self.auditor and self.audited_at):
            raise AuditRefused("session, auditor and audited_at are required")


class TranscriptAudits:
    def __init__(self, root: Path, terms: RunTerms = V2_TERMS):
        self.root, self.terms = Path(root), terms

    def get(self, day: date, book: str) -> TranscriptAudit | None:
        path = self.root / self.terms.transcript_audit_path(day, book)
        return TranscriptAudit(**json.loads(path.read_text(encoding="utf-8"))) if path.is_file() else None

    def record(self, day: date, audit: TranscriptAudit) -> str:
        path = self.root / self.terms.transcript_audit_path(day, audit.book)
        if path.is_file():
            raise AuditRefused(f"{path.relative_to(self.root)} already exists (written once)")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(audit), sort_keys=True, indent=1) + "\n", encoding="utf-8")
        return str(path.relative_to(self.root))


def new_audit(day: date, book: str, fired: dict, breaches: list[str], evidence: str, auditor: str, now: datetime,
              session: str = "") -> TranscriptAudit:  # fmt: skip
    """An audit of the session the fire log names for that book-day (or `session`, when the fire gave no link)."""
    if not fired.get("fired"):
        raise AuditRefused(f"{book} was not fired on {day}: no session to audit")
    return TranscriptAudit(book, day.isoformat(), fired["version"], fired.get("session") or session,
                           BREACH if breaches else CLEAN, breaches, evidence, auditor, now.isoformat())  # fmt: skip
