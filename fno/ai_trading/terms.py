"""The decision run's terms (story F1t revision 2): G11's `RunTerms`, a third instance beside v2's and v4's, built from
`ai_books.decision_timing`. `fno/ai`'s chain (`read_submission`, `TranscriptAudits`, `stop_reason`, `fired_sessions`,
the audit draws) serves decisions through it with no new parameter and no copy."""

from __future__ import annotations

from ..ai.run_terms import RunTerms
from .paths import DECISION_RUN, DECISIONS_FOLDER
from .timing import DecisionTiming


def decision_terms(timing: DecisionTiming) -> RunTerms:
    return RunTerms(DECISION_RUN, DECISIONS_FOLDER, timing.receipt_deadline, timing.reveal_from, timing.reveal_deadline)
