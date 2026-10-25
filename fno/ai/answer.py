"""A book's answer (stories F1 and G5): per question a probability (or null for "no forecast") and its reason, plus
the model the session reports. Protocol v4's point questions (V1, V2: `terms.POINT_QUESTIONS`) take a `value`
instead, a variance in the protocol's own unit (squared log returns), finite and above 0; one above its question's
`VARIANCE_CAP` is refused as a unit error (G11 C2; the caps tightened after review). Percent squared and volatility
points always land above them; an annualised figure does for V1 (a 15% volatility is 0.0225 > 0.01) but not for V2
below a VIX of about 22.4 (0.0225 < 0.05): a known gap, pinned by a test. The routine writes only those parts;
`seal` adds the book, day, hashes and version from its own pointer and export, so the model cannot mislabel them. The
same checks run when sealing (the model can fix a refused answer before the deadline) and when collecting (nothing
unchecked becomes a record)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from ..constants import FORECAST_QUESTIONS, V1_RV_1S, V2_RV_5S, V3_RV_20S
from ..forecast_v4.terms import POINT_QUESTIONS
from .envelope import Envelope
from .pointer import is_number, is_probability

MAX_REASON_CHARS = 600
MAX_MODEL_CHARS = 100
# A forecast is an expected variance, so it sits far below the largest one ever realised (strong evidence, NIFTY's
# official closes 2017-2026: one session's close-proxy RV_s at most 0.0193, 23 Mar 2020; 5 sessions 0.0287; 20
# sessions 0.064). Above these it is a unit mistake. A standard deviation given for V1 (about 0.008) still passes, and
# so does an annualised V2 below a VIX of about 22.4 (judge 586 m2).
VARIANCE_CAP = {V1_RV_1S: 0.01, V2_RV_5S: 0.05, V3_RV_20S: 0.2}
ANSWER_FIELDS = ("book", "day", "export_sha256", "forecasts", "model_reported", "pack_sha256", "version")


class AnswerRefused(ValueError):
    """The answer as a whole is unusable (wrong shape); the message says why."""


@dataclass(frozen=True)
class CheckedAnswer:
    probabilities: dict[str, float | None]  # question -> value kept: a probability, or a v4 variance (None: none)
    problems: dict[str, str]  # question -> why its value was refused ('' when kept)
    model_reported: str


def complete_answer(draft: dict, labels: dict) -> dict:
    """The full answer: the routine's draft (`model_reported`, `forecasts`) and the labels its pointer fixes."""
    if not isinstance(draft, dict) or sorted(draft) != ["forecasts", "model_reported"]:
        raise AnswerRefused("the answer must have exactly the fields forecasts and model_reported")
    return {**labels, **draft}


def check_answer(answer: dict, labels: dict, envelope: Envelope | None,
                 questions: Sequence[str] = FORECAST_QUESTIONS) -> CheckedAnswer:  # fmt: skip
    """Every question's outcome, or AnswerRefused when the labels or the shape are wrong. `questions`: the day's (v2's
    five, or a v4 pointer's list)."""
    if not isinstance(answer, dict) or sorted(answer) != list(ANSWER_FIELDS):
        raise AnswerRefused(f"the answer must have exactly the fields {', '.join(ANSWER_FIELDS)}")
    wrong = [name for name, value in labels.items() if answer[name] != value]
    if wrong:
        raise AnswerRefused(f"answer is not for this input: {', '.join(wrong)} differ")
    model = answer["model_reported"]
    if not isinstance(model, str) or not model.strip() or len(model) > MAX_MODEL_CHARS:
        raise AnswerRefused('model_reported must be short text ("unknown" when the session cannot tell)')
    forecasts = answer["forecasts"]
    if not isinstance(forecasts, dict) or sorted(forecasts) != sorted(questions):
        raise AnswerRefused(f"forecasts must name exactly {', '.join(questions)}")
    kept, problems = {}, {}
    for question in questions:
        cap = VARIANCE_CAP.get(question) if question in POINT_QUESTIONS else None
        value, problem = _question(forecasts[question], cap)
        problem = problem or (envelope.problem(question, value) if envelope else "")
        kept[question], problems[question] = (None if problem else value), problem
    return CheckedAnswer(kept, problems, model.strip())


def _question(entry, cap: float | None) -> tuple[float | None, str]:
    """`cap`: a point question's variance cap; None for a probability."""
    point = cap is not None
    key = "value" if point else "probability"
    if not isinstance(entry, dict) or sorted(entry) != sorted((key, "reason")):
        return None, f'must be {{"{key}": ..., "reason": ...}}'
    value, reason = entry[key], entry["reason"]
    if not isinstance(reason, str) or not reason.strip() or "\n" in reason or len(reason) > MAX_REASON_CHARS:
        return None, f"reason must be one line of 1 to {MAX_REASON_CHARS} characters"
    if value is None:
        return None, ""
    if point and not (is_number(value) and 0 < value <= cap):
        return None, f"value must be a variance above 0 and at most {cap:g} (squared log returns) or null"
    if not point and not is_probability(value):
        return None, "probability must be a number in [0, 1] or null"
    return float(value), ""
