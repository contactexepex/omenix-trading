"""One fired run as the book side sees it, whatever its protocol (stories F1/G5 and G11 step 7): the book, the day, the
run's terms (paths, deadline, reveal time), the input the model is shown, the labels every answer must carry, Hybrid's
envelope and the day's questions. The fired text names its protocol: a v4 pointer says `"kind": "forecast_v4"` and
carries its whole input; anything else is read as F1's v2 pointer, whose input is built from the committed pack.
Standard library only: the routine reads it."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from ..constants import FORECAST_QUESTIONS
from .envelope import Envelope
from .export import export_sha256
from .pointer import BookPointer, parse_pointer
from .run_terms import V2_TERMS, V4_TERMS, RunTerms
from .v4_pointer import KIND, parse_v4_pointer, v4_envelope, v4_labels
from .versions import version_by_label


@dataclass(frozen=True)
class BookRun:
    book: str
    day: date
    terms: RunTerms
    export: dict  # the input shown to the model
    labels: dict  # what every answer must carry (the book cannot mislabel them)
    envelope: Envelope | None  # Hybrid's; None for Book 3
    questions: tuple[str, ...]


def read_run(text: str, v2_export: Callable[[BookPointer], dict]) -> BookRun:
    """The run the fired `text` names. `v2_export(pointer)`: a v2 run's input (built by `brief`, read back later)."""
    if _is_v4(text):
        pointer = parse_v4_pointer(text)
        built = pointer.input
        return BookRun(pointer.book, pointer.day, V4_TERMS, built, v4_labels(built), v4_envelope(built),
                       tuple(built["questions"]))  # fmt: skip
    pointer = parse_pointer(text)
    export = v2_export(pointer)
    return BookRun(pointer.book, pointer.day, V2_TERMS, export, answer_labels(pointer, export), envelope_of(pointer),
                   FORECAST_QUESTIONS)  # fmt: skip


def answer_labels(pointer: BookPointer, export: dict) -> dict:
    """What a v2 pointer and its export fix in every answer: the book cannot mislabel them."""
    return {"book": pointer.book, "day": pointer.day.isoformat(), "export_sha256": export_sha256(export),
            "pack_sha256": pointer.pack_sha256, "version": pointer.version}  # fmt: skip


def envelope_of(pointer: BookPointer) -> Envelope | None:
    """Hybrid's v2 envelope around its pointer's baselines; None for Book 3."""
    width = version_by_label(pointer.version).envelope_width
    return Envelope.from_rules(pointer.rules, width) if pointer.rules is not None else None


def _is_v4(text: str) -> bool:
    try:
        fields = json.loads(text)
    except ValueError:
        return False
    return isinstance(fields, dict) and fields.get("kind") == KIND
