"""Material terms (NP5b; NP0 section 2h): `MaterialTerms` gives a headline a weight from the owner's weighted terms, and
`is_material` says whether an article is worth a page read first: its weight is at least 1 AND its title names exactly
one company with high confidence (agentic's selection, as a rule; none of its numbers). Every headline is still
recorded; this only orders what is read. The terms are the owner's private content (`config/materiality-vN.json`,
never in the repository); a term is a safe pattern (the one grammar), matched against at most `MAX_TEXT` characters of
the title, each term counting once."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from fno.ingestion.news import codes
from fno.ingestion.news.safe_pattern import compile_safe
from fno.ingestion.news.tagging.tagger import HIGH, Tag
from fno.ingestion.news.tagging.text import capped
from fno.ingestion.news.text_rules import without_outlet

FORMAT = 1
MAX_TERMS = 200
MAX_WEIGHT = 10.0
MATERIAL_AT = 1.0
TOP_KEYS = frozenset({"format", "terms"})
TERM_KEYS = frozenset({"pattern", "weight"})


class MaterialityError(Exception):
    """`str(error)` is one of the fixed codes."""


@dataclass(frozen=True)
class Term:
    pattern: re.Pattern
    weight: float


class MaterialTerms:
    def __init__(self, terms: tuple[Term, ...], version: int = 0, sha256: str = ""):
        self.terms, self.version, self.sha256 = terms, version, sha256

    def weight(self, title: str | None, source: str | None = None) -> float:
        """`source`: the outlet name, whose " - Outlet" suffix on a title is not about the story (judge 95 F1)."""
        text = without_outlet(capped(title), source)
        return sum(term.weight for term in self.terms if term.pattern.search(text))

    def is_material(self, title: str | None, tag: Tag, source: str | None = None) -> bool:
        return self.weight(title, source) >= MATERIAL_AT and tag.confidence == HIGH


def parse_terms(data: bytes, version: int, sha256: str = "") -> MaterialTerms:
    """The terms of a file; `MaterialityError(materiality_invalid)` for anything that is not a whole, safe file."""
    try:
        document = json.loads(data)
    except (ValueError, UnicodeDecodeError):
        raise _invalid() from None
    if not isinstance(document, dict) or set(document) != TOP_KEYS or document["format"] != FORMAT:
        raise _invalid()
    entries = document["terms"]
    if not isinstance(entries, list) or not 0 < len(entries) <= MAX_TERMS:
        raise _invalid()
    terms, seen = [], set()
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != TERM_KEYS:
            raise _invalid()
        pattern, weight = entry["pattern"], entry["weight"]
        if not isinstance(pattern, str) or pattern.casefold() in seen or not _good_weight(weight):
            raise _invalid()
        try:
            terms.append(Term(compile_safe(pattern), float(weight)))
        except ValueError:
            raise _invalid() from None
        seen.add(pattern.casefold())
    return MaterialTerms(tuple(terms), version, sha256)


def _good_weight(weight: object) -> bool:
    return isinstance(weight, (int, float)) and not isinstance(weight, bool) and 0 < weight <= MAX_WEIGHT


def _invalid() -> MaterialityError:
    return MaterialityError(codes.MATERIALITY_INVALID)
