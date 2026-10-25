"""What one AI book's day comes to (stories F1 and G5): its status, the probabilities that count, and everything the
audit keeps. Only an on-time, revealed, valid answer from the registered model, unexposed to the other book's answer,
gives probabilities; every other case records "no forecast" for the questions concerned, never an imputed value. The
attempted values stay in the audit file."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, datetime

from ..constants import FORECAST_QUESTIONS
from .answer import AnswerRefused, check_answer
from .envelope import Envelope
from .run_terms import V2_TERMS, RunTerms
from .seal import SealBroken, open_reveal
from .submissions import Submission
from .versions import BookVersion

ON_TIME, LATE, NOT_REVEALED, INVALID = "on_time", "late", "not_revealed", "invalid"
NOT_FIRED, NO_SUBMISSION, EXPOSED, MODEL_MISMATCH = "not_fired", "no_submission", "exposed", "model_mismatch"
UNKNOWN_MODEL = "unknown"


@dataclass
class Outcome:
    book: str
    status: str
    version: str = ""  # the registered version label the records carry
    questions: tuple[str, ...] = FORECAST_QUESTIONS  # the day's questions (v2's five, or a v4 pointer's list)
    probabilities: dict[str, float | None] = field(default_factory=dict)
    problems: dict[str, str] = field(default_factory=dict)
    attempted: dict = field(default_factory=dict)
    model_reported: str = ""
    model_check: str = ""
    committed_at: datetime | None = None
    revealed_at: datetime | None = None
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.probabilities = self.probabilities or dict.fromkeys(self.questions)

    def withdraw(self, status: str, note: str) -> None:
        """No probability counts any more (the attempted values stay in the audit)."""
        self.status, self.probabilities = status, dict.fromkeys(self.questions)
        self.notes.append(note)


def model_check(reported: str, registered: str) -> str:
    def plain(name: str) -> str:
        return name.split("[")[0].strip().lower()

    if plain(reported) in ("", UNKNOWN_MODEL):
        return "unverified"
    return "match" if plain(reported) == plain(registered) else "mismatch"


def judge(book: str, day: date, submission: Submission, labels: dict, envelope: Envelope | None,
          version: BookVersion, terms: RunTerms = V2_TERMS,
          questions: Sequence[str] = FORECAST_QUESTIONS) -> Outcome:  # fmt: skip
    """The book's outcome from its submission, before the cross-book exposure check."""
    commitment, reveal = submission.sealed(), submission.reveal
    outcome = Outcome(book, ON_TIME, version.label, tuple(questions), notes=list(submission.notes))
    if submission.commitment is None:
        outcome.withdraw(NO_SUBMISSION, "no commitment in the repository (the AI was unavailable)")
        return outcome
    outcome.committed_at = submission.commitment.received_at
    outcome.revealed_at = reveal.received_at if reveal else None
    if commitment is None:
        outcome.withdraw(INVALID, "the commitment file is not a commitment")
        return outcome
    if reveal is None or reveal.received_at is None or reveal.received_at > terms.reveal_deadline(day):
        outcome.withdraw(NOT_REVEALED, f"no reveal received by {terms.reveal_by:%H:%M} IST ({_why(reveal)})")
        return outcome
    try:
        answer = open_reveal(reveal.text, commitment)
        checked = check_answer(answer, labels, envelope, questions)
    except (SealBroken, AnswerRefused) as broken:
        outcome.withdraw(INVALID, str(broken))
        return outcome
    outcome.probabilities, outcome.problems, outcome.attempted = (
        checked.probabilities,
        checked.problems,
        answer["forecasts"],
    )
    outcome.model_reported = checked.model_reported
    outcome.model_check = model_check(checked.model_reported, version.registered_model)
    _deadline_and_model(outcome, submission, terms.receipt_deadline(day))
    return outcome


def _deadline_and_model(outcome: Outcome, submission: Submission, deadline: datetime) -> None:
    received = submission.commitment.received_at
    if received is None:
        outcome.withdraw(LATE, f"receipt time unknown, treated as late ({submission.commitment.receipt_problem})")
    elif received > deadline:
        outcome.withdraw(LATE, f"commitment received {received.isoformat()}, after {deadline:%H:%M:%S}")
    elif outcome.model_check == "mismatch":
        outcome.withdraw(MODEL_MISMATCH, f"the session reported {outcome.model_reported}, not the registered model")


def _why(reveal) -> str:
    if reveal is None:
        return "none published"
    return reveal.receipt_problem or f"received {reveal.received_at.isoformat()}"


def mark_exposures(outcomes: dict[str, Outcome]) -> None:
    """A book whose commitment GitHub received after another book's answer was readable is not independent."""
    for book, outcome in outcomes.items():
        for other, seen in outcomes.items():
            readable = seen.revealed_at
            if other != book and outcome.status == ON_TIME and readable and readable < outcome.committed_at:
                outcome.withdraw(
                    EXPOSED, f"{other}'s answer was public at {readable.isoformat()}, before this commitment"
                )
