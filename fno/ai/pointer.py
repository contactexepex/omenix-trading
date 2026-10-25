"""What the forecast-capture job fires each AI book's routine with (stories F1 and G5): one line of JSON naming the
book, the day, the pack's SHA-256 and the book's registered version, plus, for Hybrid only, the rules' numbers of the
day. The routine receives it as untrusted text, so reading it back checks every field and refuses anything else
before any input is shown to the model."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from datetime import date

from ..constants import (
    BASELINE_BASE_RATE,
    BASELINE_MODEL,
    BASELINE_RISK_NEUTRAL,
    BOOK1_RULES,
    BOOK2_HYBRID,
    FORECAST_QUESTIONS,
)
from .versions import VersionRefused, current_version

POINTER_FIELDS = ("book", "day", "pack_sha256", "rules", "version")
RULE_FORECASTERS = (BASELINE_RISK_NEUTRAL, BASELINE_BASE_RATE, BASELINE_MODEL, BOOK1_RULES)
SHA256 = re.compile(r"[0-9a-f]{64}")
MAX_POINTER_BYTES = 4096

Rules = dict[str, dict[str, float | None]]  # question -> rule forecaster -> probability (None: no forecast)


class PointerRefused(ValueError):
    """The text is not a pointer this project wrote; the message names the first thing wrong."""


@dataclass(frozen=True)
class BookPointer:
    book: str
    day: date
    pack_sha256: str
    version: str  # the registered version label
    rules: Rules | None = field(default=None)  # Hybrid only

    def to_text(self) -> str:
        fields = {"book": self.book, "day": self.day.isoformat(), "pack_sha256": self.pack_sha256,
                  "rules": self.rules, "version": self.version}  # fmt: skip
        return json.dumps(fields, sort_keys=True, separators=(",", ":"))


def parse_pointer(text: str) -> BookPointer:
    if len(text.encode("utf-8")) > MAX_POINTER_BYTES:
        raise PointerRefused("longer than any pointer")
    try:
        fields = json.loads(text)
    except ValueError as error:
        raise PointerRefused(f"not JSON ({error.msg})") from None
    if not isinstance(fields, dict) or sorted(fields) != list(POINTER_FIELDS):
        raise PointerRefused(f"fields must be exactly {', '.join(POINTER_FIELDS)}")
    try:
        version = current_version(fields["book"] if isinstance(fields["book"], str) else "")
        day = date.fromisoformat(fields["day"])
    except (VersionRefused, TypeError, ValueError) as error:
        raise PointerRefused(str(error)) from None
    if fields["version"] != version.label:
        raise PointerRefused("version is not the book's registered version")
    if not isinstance(fields["pack_sha256"], str) or not SHA256.fullmatch(fields["pack_sha256"]):
        raise PointerRefused("pack_sha256 is not a SHA-256")
    rules = _rules(fields["rules"], fields["book"])
    return BookPointer(fields["book"], day, fields["pack_sha256"], version.label, rules)


def _rules(value, book: str) -> Rules | None:
    if book != BOOK2_HYBRID:
        if value is not None:
            raise PointerRefused(f"{book} never receives the rules' numbers")
        return None
    if not isinstance(value, dict) or sorted(value) != sorted(FORECAST_QUESTIONS):
        raise PointerRefused("rules must name exactly the five questions")
    for by_name in value.values():
        if not isinstance(by_name, dict) or sorted(by_name) != sorted(RULE_FORECASTERS):
            raise PointerRefused(f"each question's rules must name exactly {', '.join(RULE_FORECASTERS)}")
        if not all(is_probability(p) or p is None for p in by_name.values()):
            raise PointerRefused("a rule's value must be a probability in [0, 1] or null")
    return value


def is_number(value) -> bool:
    """A finite JSON number (never a bool); an integer too large for a float is not one (never an OverflowError)."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def is_probability(value) -> bool:
    return is_number(value) and 0 <= value <= 1
