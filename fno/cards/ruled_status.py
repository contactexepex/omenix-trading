"""The card's status with T2's rule checks (story T2): T1's `RegistryStatus` reading, unchanged, then one line per rule
outcome. The status's reason becomes `data_check_failed` (an unreadable record, or C3 refused the execution
capture) or `hard_rule_breach` (C4 refused a trade today) only when a committed record says so, then `step_problems`
(story T1e: a desk step failed or was refused today, with the card's warning); T1's reason otherwise. Card v1 stays
`NO TRADE` whatever the rules say: it never shows a trade."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from datetime import date

from ..constants import CARD_DATA_CHECK_FAILED, CARD_HARD_RULE_BREACH, CARD_STEP_PROBLEMS
from .problem_steps import ProblemSteps, StepFindings
from .rule_checks import RuleOutcome, RuleSource, UnreadableRecord
from .sections import StatusReading, StatusSource

NO_BREACH = "Rule checks: no breach"
NO_BREACH_WARNED = "Rule checks: no breach (rule checks only; see the warning above)"  # T1e: never a bare all-clear
NOT_COMPLETE = "Rule checks: not complete"
REFUSED = "Rule checks: a rule refused, or a record could not be read"
SEVERITY = (CARD_DATA_CHECK_FAILED, CARD_HARD_RULE_BREACH, CARD_STEP_PROBLEMS)  # the first found decides the reason


class RuleChecks:
    def __init__(self, sources: Sequence[RuleSource]):
        self.sources = tuple(sources)

    def outcomes(self, day: date) -> list[RuleOutcome]:
        return [_read(source, day) for source in self.sources]


def _read(source: RuleSource, day: date) -> RuleOutcome:
    try:
        return source.outcome(day)
    except UnreadableRecord as unreadable:
        return RuleOutcome(source.name, True, str(unreadable), CARD_DATA_CHECK_FAILED)


def summary(outcomes: Sequence[RuleOutcome], warned: bool = False) -> str:
    if any(o.code for o in outcomes):
        return REFUSED
    if not all(o.final for o in outcomes):
        return NOT_COMPLETE
    return NO_BREACH_WARNED if warned else NO_BREACH


def reason_code(base: str, outcomes: Sequence[RuleOutcome], added: str | None = None) -> str:
    found = {base} | {o.code for o in outcomes} | ({added} if added else set())
    return next((code for code in SEVERITY if code in found), base)


class RuledStatus(StatusSource):
    """`problems`: story T1e's findings on today's failed or refused steps. Their code joins the reason's severity
    order and their warning qualifies a bare "no breach"; the card shows the warning itself (`CardBuilder`)."""

    def __init__(self, base: StatusSource, checks: RuleChecks, problems: ProblemSteps | None = None):
        self.base, self.checks, self.problems = base, checks, problems

    def status(self, day: date) -> StatusReading:
        reading, outcomes = self.base.status(day), self.checks.outcomes(day)
        found = self.problems.findings(day) if self.problems else StepFindings()
        code = reason_code(reading.reason_code, outcomes, found.code)
        _, *rest = reading.section.lines  # T1's first line is the status line; the reason may change it
        lines = (f"Status: {reading.status} ({code})", *rest, summary(outcomes, found.warning is not None),
                 *(f"- {o.name}: {o.line}" for o in outcomes))  # fmt: skip
        used = reading.section.used + tuple(u for o in outcomes for u in o.used)
        return StatusReading(reading.status, code, replace(reading.section, lines=lines, used=used))
