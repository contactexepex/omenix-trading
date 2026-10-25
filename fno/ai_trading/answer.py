"""An AI book's decision answer (story F1t). The routine writes only the three model fields and `decision`; `seal`
adds the labels its pointer fixes (book, day, version, both pack hashes, the cards item's hash), so the model cannot
mislabel them. The same checks run when sealing (the model can fix a refused answer before the deadline) and when
collecting (nothing unchecked reaches a decider): the labels, the model rule, F1t's base shape (an object with a text
`action` and a one-line `reason`; what it decides is the book's own, checked by F5's or F6's `check_decision`) and the
private-figure rule."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

from ..desk.pack_items import canonical_json, sha256_hex
from .figures import figure_problems
from .pointer import DecisionPointer

DRAFT_FIELDS = ("decision", "model_configured", "model_reported", "model_source")
LABELS = ("book", "cards_sha256", "common_pack_sha256", "day", "private_pack_sha256", "version")
ANSWER_FIELDS = tuple(sorted(LABELS + DRAFT_FIELDS))
UNKNOWN_MODEL = "unknown"
SESSION_TOOL, INSTRUCTIONS, NO_SOURCE = "session_tool", "instructions", "none"  # where the model fields came from
MODEL_SOURCES = (SESSION_TOOL, INSTRUCTIONS, NO_SOURCE)
MODEL_ID = re.compile(r"[a-z][a-z0-9.-]{2,80}(\[[a-z0-9]{1,8}\])?")
MAX_REASON_CHARS = 600
MODEL_RULE = (
    "MODEL RULE (story F1t): after writing your decision, call the session-description tool (get_session, no session "
    "ID) and copy model_reported = external_metadata.last_served_model (the model that served you) and "
    'model_configured = session_context.model, with model_source "session_tool". Without that tool, set '
    "model_reported = the exact model ID your own instructions state, model_configured the same, model_source "
    '"instructions". With neither, all three "unknown" except model_source "none". Only the tool counts as verified: '
    "any other source, an unknown model or a model other than the registered one means no trade today. The transcript "
    "audit compares what you copied with the tool's answer."
)


class AnswerRefused(ValueError):
    """The answer cannot be used; the message lists every problem, so the model can fix them all at once."""


@dataclass(frozen=True)
class CheckedAnswer:
    decision: dict
    model_reported: str  # the served model (`last_served_model`) when the source is the session tool
    model_configured: str
    model_source: str


def labels_of(pointer: DecisionPointer) -> dict:
    return {"book": pointer.book, "cards_sha256": sha256_hex(canonical_json(pointer.analyst_cards)),
            "common_pack_sha256": pointer.common_pack_sha256, "day": pointer.day.isoformat(),
            "private_pack_sha256": pointer.private_pack_sha256, "version": pointer.version}  # fmt: skip


def complete_answer(draft, labels: dict) -> dict:
    if not isinstance(draft, dict) or sorted(draft) != list(DRAFT_FIELDS):
        raise AnswerRefused(f"the answer must have exactly the fields {', '.join(DRAFT_FIELDS)}")
    return {**labels, **draft}


def check_answer(answer, labels: dict, shape_check: Callable[[dict], list[str]], private: set[str]) -> CheckedAnswer:
    if not isinstance(answer, dict) or sorted(answer) != list(ANSWER_FIELDS):
        raise AnswerRefused(f"the answer must have exactly the fields {', '.join(ANSWER_FIELDS)}")
    wrong = [name for name in LABELS if answer[name] != labels[name]]
    if wrong:
        raise AnswerRefused(f"the answer is not for this input: {', '.join(wrong)} differ")
    decision = answer["decision"]
    problems = model_problems(answer) + base_problems(decision)
    if not problems:
        problems = list(shape_check(decision)) + figure_problems(decision, private)
    if problems:
        raise AnswerRefused("; ".join(problems))
    return CheckedAnswer(decision, answer["model_reported"], answer["model_configured"], answer["model_source"])


def model_problems(answer: dict) -> list[str]:
    problems = [f'{name} must be the exact model ID (for example "claude-opus-5-5") or "{UNKNOWN_MODEL}"'
                for name in ("model_reported", "model_configured") if not _is_model(answer[name])]  # fmt: skip
    if answer["model_source"] not in MODEL_SOURCES:
        problems.append(f"model_source must be one of {', '.join(MODEL_SOURCES)}")
    elif answer["model_source"] == NO_SOURCE and answer["model_reported"] != UNKNOWN_MODEL:
        problems.append(f'model_source "{NO_SOURCE}" goes with model_reported "{UNKNOWN_MODEL}"')
    return problems


def _is_model(name) -> bool:
    return isinstance(name, str) and (name == UNKNOWN_MODEL or MODEL_ID.fullmatch(name) is not None)


def base_problems(decision) -> list[str]:
    if not isinstance(decision, dict):
        return ["decision must be an object"]
    action = decision.get("action")
    if not isinstance(action, str) or not action.strip():
        return ["decision.action must be text (the book's own action)"]
    reason = decision.get("reason")
    if not isinstance(reason, str) or not reason.strip() or "\n" in reason or len(reason) > MAX_REASON_CHARS:
        return [f"decision.reason must be one line of 1 to {MAX_REASON_CHARS} characters"]
    return []
