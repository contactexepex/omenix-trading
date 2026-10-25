"""What one AI book's decision day comes to before any decider runs (story F1t, the judging table): the first rule that
applies decides the status. Only `accepted` goes on to the book's decider; every other status is no trade, with its
reason recorded and named in the step's one alert. A commit's receipt is the first valid reading of the remote that
held it (`ObservedPushes`): at the receipt deadline for an on-time commitment, never later."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from ..ai.fire_once import FIRE_UNKNOWN, FIRED, FIRING
from ..ai.outcome import EXPOSED, INVALID, LATE, MODEL_MISMATCH, NO_SUBMISSION, NOT_FIRED, NOT_REVEALED
from ..ai.outcome import model_check as compare_models
from ..ai.receipts import PushReceipts, ReceiptUnknown
from ..ai.seal import Commitment, SealBroken, open_reveal
from ..ai.submissions import Submission
from .answer import SESSION_TOOL, AnswerRefused, CheckedAnswer, check_answer

ACCEPTED, MODEL_UNVERIFIED, REFUSED, PROMOTED = "accepted", "model_unverified", "refused", "promoted"
JUDGE_FAILED = "judge_failed"  # the judge's verdict blocked (Book 2): the "no trade, judge failed" run is committed
NOT_TRADED = (NOT_FIRED, NO_SUBMISSION, LATE, EXPOSED, INVALID, NOT_REVEALED, MODEL_MISMATCH, MODEL_UNVERIFIED,
              JUDGE_FAILED, REFUSED)  # fmt: skip
NO_COMMITMENT = "no commitment (the AI was unavailable or limited)"
NOT_ON_TIME = "commitment not on the remote at {at:%H:%M:%S} ({why})"
OTHERS_EARLY = "{books} revealed before {at:%H:%M:%S}: their answer could be read"
OWN_EARLY = "revealed before {at:%H:%M:%S} (the reveal waits for every seal)"
NO_REVEAL = "no reveal on the remote at {at:%H:%M:%S}"
MISMATCH = "the session was served by {reported} (configured {configured}), not the registered {registered}"
UNVERIFIED = "the model is not verified (source {source}: only the session tool's served model counts): no trade"


@dataclass
class DayOutcome:
    book: str
    status: str
    reason: str = ""
    version: str = ""
    model_reported: str = ""  # the served model the session copied from its session tool
    model_configured: str = ""
    model_source: str = ""
    model_check: str = ""
    strategy_label: str = ""  # a promoted run's: "strategy passed" or "strategy not yet passed"; "" with no trade
    commitment_commit: str = ""
    reveal_commit: str = ""
    received: dict = field(default_factory=dict)  # "commitment"/"reveal" -> deadline it was first seen at, or None
    answer: CheckedAnswer | None = None  # kept only while accepted, for the decider

    def stop(self, status: str, reason: str) -> DayOutcome:
        self.status, self.reason, self.answer = status, reason, None
        return self


@dataclass(frozen=True)
class Deadlines:
    receipt: datetime  # a commitment counts only if on the remote then
    reveal: datetime  # a reveal counts only if on the remote by then


@dataclass(frozen=True)
class Judged:
    """What the judge needs about one book, all read before any book is judged."""

    fired: dict  # the fire log's entry
    labels: dict  # what the fired pointer fixes (`answer.labels_of`)
    submission: Submission
    shape_check: object  # the version's `check_decision`
    private: set[str]  # the private figures of the book's pack (`figures.private_figures`)
    registered_model: str


def judge(
    book: str, facts: Judged, receipts: PushReceipts, deadlines: Deadlines, others_early: list[str]
) -> DayOutcome:
    """`others_early`: the other books whose reveal was already on the remote at the receipt deadline."""
    outcome = DayOutcome(book, ACCEPTED, version=facts.labels.get("version", ""))
    if facts.fired.get("state") not in (FIRED, FIRE_UNKNOWN, FIRING):  # a leftover `firing`: it may have started
        return outcome.stop(NOT_FIRED, facts.fired.get("reason") or "not fired")
    commitment, reveal = facts.submission.commitment, facts.submission.reveal
    if commitment is None:
        return outcome.stop(NO_SUBMISSION, NO_COMMITMENT)
    outcome.commitment_commit = commitment.commit
    outcome.received["commitment"] = seen_at(receipts, commitment.commit)
    if outcome.received["commitment"] != deadlines.receipt:
        return outcome.stop(LATE, NOT_ON_TIME.format(at=deadlines.receipt, why=_why(receipts, commitment.commit)))
    if others_early:
        return outcome.stop(EXPOSED, OTHERS_EARLY.format(books=", ".join(others_early), at=deadlines.receipt))
    if reveal is not None:
        outcome.reveal_commit = reveal.commit
        outcome.received["reveal"] = seen_at(receipts, reveal.commit)
        if outcome.received["reveal"] == deadlines.receipt:
            return outcome.stop(INVALID, OWN_EARLY.format(at=deadlines.receipt))
    if reveal is None or outcome.received.get("reveal") != deadlines.reveal:
        return outcome.stop(NOT_REVEALED, NO_REVEAL.format(at=deadlines.reveal))
    return _check(outcome, facts, commitment_text=commitment.text, reveal_text=reveal.text)


def _check(outcome: DayOutcome, facts: Judged, commitment_text: str, reveal_text: str) -> DayOutcome:
    try:
        answer = open_reveal(reveal_text, Commitment.from_text(commitment_text))
        checked = check_answer(answer, facts.labels, facts.shape_check, facts.private)
    except (SealBroken, AnswerRefused) as broken:
        return outcome.stop(INVALID, str(broken))
    outcome.model_reported, outcome.model_configured = checked.model_reported, checked.model_configured
    outcome.model_source = checked.model_source
    outcome.model_check = served_model_check(checked, facts.registered_model)
    if outcome.model_check == "mismatch":
        return outcome.stop(MODEL_MISMATCH, MISMATCH.format(reported=checked.model_reported,
                                                            configured=checked.model_configured,
                                                            registered=facts.registered_model))  # fmt: skip
    if outcome.model_check != "match":
        return outcome.stop(MODEL_UNVERIFIED, UNVERIFIED.format(source=checked.model_source))
    outcome.answer = checked
    return outcome


def served_model_check(checked: CheckedAnswer, registered: str) -> str:
    """ "match" only when the session tool reported both its served and its configured model as the registered one
    (judges 621 and 623; the orchestrator's ruling: an instructions line alone is not verified)."""
    if checked.model_source != SESSION_TOOL:
        return "unverified"
    checks = {compare_models(checked.model_reported, registered), compare_models(checked.model_configured, registered)}
    return "mismatch" if "mismatch" in checks else "match" if checks == {"match"} else "unverified"


def seen_at(receipts: PushReceipts, commit: str) -> datetime | None:
    try:
        return receipts.received_at(commit)
    except ReceiptUnknown:
        return None


def _why(receipts: PushReceipts, commit: str) -> str:
    try:
        return f"first seen {receipts.received_at(commit):%H:%M:%S}"
    except ReceiptUnknown as unknown:
        return str(unknown)
