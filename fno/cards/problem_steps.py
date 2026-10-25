"""The card's warning about the desk steps that failed or were refused today (stories T1d and T1e): read from the
committed run log through T2's reader, with O1's own rule (`problem_steps`), never by matching text. A run log that
exists but cannot be read is a warning too, since the card then cannot say which steps worked. Nothing when all is
well. The card shows the warning on its own (`WarningSource`), so a failing status source never hides it."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from ..constants import CARD_DATA_CHECK_FAILED, CARD_STEP_PROBLEMS
from ..desk.run_log import problem_steps
from .rule_checks import RunLogReader, UnreadableRecord
from .sections import CardWarning, WarningSource

GLYPH = "⚠️ WARNING:"  # the word and the glyph, never colour alone (owner, 24 Oct 2026)
FAILED_HEADLINE = f"{GLYPH} part of today's desk run did not work."
DETAIL = "Steps with problems today: {steps}. Their alerts in #fno-desk give the reasons."  # T1d's list
UNREADABLE = CardWarning(
    f"{GLYPH} today's run log could not be read.", "This card cannot say which desk steps worked. See #fno-desk."
)


@dataclass(frozen=True)
class StepFindings:
    """What the run log says: the warning, and the reason code it adds (`step_problems` for problem steps,
    `data_check_failed` for an unreadable log, whatever the rule checks say); both None on a clean day."""

    warning: CardWarning | None = None
    code: str | None = None


class ProblemSteps(WarningSource):
    def __init__(self, runs: RunLogReader):
        self.runs = runs

    def findings(self, day: date) -> StepFindings:
        try:
            steps, _ = self.runs.steps(day)
        except UnreadableRecord:  # T2's rule checks name the file; the warning puts the doubt in the headline
            return StepFindings(UNREADABLE, CARD_DATA_CHECK_FAILED)
        found = problem_steps(steps or {})  # O1's one rule; the reader has already refused an odd shape
        if not found:
            return StepFindings()
        listed = ", ".join(f"{name} ({status})" for name, status in found)  # the status only: reasons are in alerts
        return StepFindings(CardWarning(FAILED_HEADLINE, DETAIL.format(steps=listed)), CARD_STEP_PROBLEMS)

    def warning(self, day: date) -> CardWarning | None:
        return self.findings(day).warning
