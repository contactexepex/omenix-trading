"""Whether an AI book-day may be scored (owner's conditions 1 and 2, 14 Oct 2026; the one rule story G4's AI reader
must call, so the rule lives in one place). Scored only when the collection said `on_time` and the transcript audit
did not find a breach; a day the audit rule selected but nobody audited yet, or a day whose week is not drawn yet, is
`pending` (not scored yet, never scored as clean by default)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .audit_plan import fired_sessions, first_days, sessions_to_audit
from .draw_seed import Week, WeekSeed
from .outcome import ON_TIME
from .run_terms import V2_TERMS, RunTerms
from .transcript_audit import BREACH, TranscriptAudits

SCORED, UNSCORED, PENDING = "scored", "unscored", "pending"


@dataclass(frozen=True)
class ScoringStatus:
    status: str  # scored, unscored or pending
    reason: str
    isolation: str  # the label every report shows beside the AI books' scores

    @property
    def scored(self) -> bool:
        return self.status == SCORED


def scoring_status(root: Path, day: date, book: str, seeds: dict[Week, WeekSeed],
                   terms: RunTerms = V2_TERMS) -> ScoringStatus:  # fmt: skip
    """`seeds`: the weekly draws' verified seeds (`fno.ai.wiring.build_audit_seeds`); none means no week is drawn."""
    collected = Path(root) / terms.audit_path(day, book)
    if not collected.is_file():
        return ScoringStatus(PENDING, "not collected", "")
    audit = json.loads(collected.read_text(encoding="utf-8"))
    isolation = audit["isolation"]
    if audit["status"] != ON_TIME:
        return ScoringStatus(UNSCORED, audit["status"], isolation)
    transcript = TranscriptAudits(root, terms).get(day, book)
    if transcript and transcript.result == BREACH:
        return ScoringStatus(UNSCORED, f"transcript breach: {', '.join(transcript.breaches)}", isolation)
    if transcript is None:
        waiting = _awaiting_audit(root, day, book, seeds, terms)
        if waiting:
            return ScoringStatus(PENDING, waiting, isolation)
    return ScoringStatus(SCORED, "on time; transcript clean or not drawn", isolation)


def _awaiting_audit(root: Path, day: date, book: str, seeds: dict[Week, WeekSeed], terms: RunTerms) -> str:
    sessions = fired_sessions(root, terms)
    if any(s.day == day and s.book == book for s in sessions_to_audit(sessions, seeds)):
        return "transcript audit due"
    if day not in first_days(sessions) and day.isocalendar()[:2] not in seeds:
        return "weekly audit draw not made yet (it waits for the week's last NIFTY 50 close, confirmed in Drive)"
    return ""
