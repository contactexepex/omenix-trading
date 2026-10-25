"""Story G11, what the AI books are fired with under protocol v4 (response 272): one line of JSON holding the book's
whole v4 input (`v4_input.py`), because a routine session has no Drive credentials and cannot read the pack. The
routine receives it as untrusted text, so reading it back checks every field before anything is shown to the model
(`v4_input_check.py`). Capped at `ROUTINE_POINTER_MAX_BYTES` (the same cap as F1t's pointer); a longer one is never
sent, so the book is `not_fired`. Standard library only: `brief` reads it in the routine.

The routine's model retypes the text into `brief` (review of dfb26381), so the pointer carries its input's SHA-256:
a single mis-copied digit is refused at `brief` with "re-copy", while the model still has time, never found later
as an invalid day. The text never holds a single quote (the routine's prompt refuses one) or a newline."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date

from ..constants import AI_BOOKS, BOOK2_HYBRID, V4_QUESTIONS
from ..constants_operations import ROUTINE_POINTER_MAX_BYTES
from .envelope import Envelope
from .pointer import SHA256, PointerRefused
from .run_terms import FORECAST_PROTOCOL_V4
from .v4_input import input_sha256
from .v4_input_check import check_v4_input
from .versions import VersionRefused, current_version

KIND = "forecast_v4"
POINTER_FIELDS = ("input", "input_sha256", "kind")
INPUT_FIELDS = ("book", "closes_before_day", "day", "derived", "history", "pack", "pack_sha256", "questions", "version")
TOO_LONG = "the pointer is {size} bytes, over the {cap}-byte cap: not fired, never truncated"
MISCOPIED = "the text is not the one fired (its input's SHA-256 differs): copy it again exactly, every character"
SINGLE_QUOTE = "'"


@dataclass(frozen=True)
class V4Pointer:
    input: dict

    @property
    def book(self) -> str:
        return self.input["book"]

    @property
    def day(self) -> date:
        return date.fromisoformat(self.input["day"])

    @property
    def input_sha256(self) -> str:
        return input_sha256(self.input)

    def to_text(self) -> str:
        """The fired text; ValueError when it would pass the cap (the caller records `not_fired`). A single quote is
        written as its JSON escape, so the text can sit inside the prompt's '...' unchanged."""
        fields = {"input": self.input, "input_sha256": self.input_sha256, "kind": KIND}
        text = json.dumps(fields, sort_keys=True, separators=(",", ":")).replace(SINGLE_QUOTE, "\\u0027")
        size = len(text.encode("utf-8"))
        if size > ROUTINE_POINTER_MAX_BYTES:
            raise ValueError(TOO_LONG.format(size=size, cap=ROUTINE_POINTER_MAX_BYTES))
        return text


def v4_labels(built: dict) -> dict:
    """What a v4 input fixes in every answer (the book cannot mislabel them); `export_sha256` holds the input's hash, so
    the answer and commitment formats stay F1's."""
    return {"book": built["book"], "day": built["day"], "export_sha256": input_sha256(built),
            "pack_sha256": built["pack_sha256"], "version": built["version"]}  # fmt: skip


def v4_envelope(built: dict) -> Envelope | None:
    """Hybrid's envelope as its input states it (checked against its rules values at parsing); None for Book 3."""
    rules = built.get("rules")
    return Envelope.from_json(rules["envelope"]) if rules else None


def parse_v4_pointer(text: str) -> V4Pointer:
    if len(text.encode("utf-8")) > ROUTINE_POINTER_MAX_BYTES:
        raise PointerRefused("longer than any pointer")
    try:
        fields = json.loads(text)
    except ValueError as error:
        raise PointerRefused(f"not JSON ({error.msg})") from None
    if not isinstance(fields, dict) or sorted(fields) != list(POINTER_FIELDS) or fields["kind"] != KIND:
        raise PointerRefused(f"fields must be exactly {', '.join(POINTER_FIELDS)}, kind {KIND}")
    built = fields["input"]
    if not isinstance(built, dict):
        raise PointerRefused("input must be an object")
    if fields["input_sha256"] != input_sha256(built):
        raise PointerRefused(MISCOPIED)
    _check_input(built)
    return V4Pointer(built)


def _check_input(built: dict) -> None:
    book = built.get("book")
    wanted = sorted(INPUT_FIELDS + (("rules",) if book == BOOK2_HYBRID else ()))
    if sorted(built) != wanted:
        raise PointerRefused(f"input fields must be exactly {', '.join(wanted)}")
    if book not in AI_BOOKS:
        raise PointerRefused(f"{book!r} is not an AI book")
    try:
        date.fromisoformat(built["day"])
        registered = current_version(book, FORECAST_PROTOCOL_V4)
    except (VersionRefused, TypeError, ValueError) as error:
        raise PointerRefused(str(error)) from None
    if built["version"] != registered.label:
        raise PointerRefused("version is not the book's registered version")
    if not isinstance(built["pack_sha256"], str) or not SHA256.fullmatch(built["pack_sha256"]):
        raise PointerRefused("pack_sha256 is not a SHA-256")
    questions = built["questions"]
    if not isinstance(questions, list) or not questions or not all(isinstance(q, str) for q in questions):
        raise PointerRefused("questions must be a non-empty list of v4 questions")
    if not set(questions) <= set(V4_QUESTIONS):
        raise PointerRefused("questions must be a non-empty list of v4 questions")
    if not set(questions) <= set(registered.questions):
        raise PointerRefused(f"{registered.label} does not define {sorted(set(questions) - set(registered.questions))}")
    check_v4_input(built, questions, registered)
