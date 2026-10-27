"""The title form two articles are compared on (P2c): lower-case, punctuation and the outlet name the feed itself gave
(when the title ends in it) removed, then word shingles. Pure text work: nothing here reads a store, a clock or the
network, and nothing is logged."""

from __future__ import annotations

import re

from fno.ingestion.news.text_rules import without_outlet

SHINGLE_WORDS = 2
NOT_WORD = re.compile(r"[\W_]+")


def title_form(title: str, source: str | None = None) -> str:
    """`source`: the outlet the feed names for the item; only a tail that IS that name is cut (`without_outlet`), so a
    headline's own " - profit rises" is never taken for an outlet (judge 115)."""
    return NOT_WORD.sub(" ", without_outlet(title, source).casefold()).strip()


def shingles(form: str) -> frozenset[str]:
    """Overlapping word groups; a one-word title is its own single shingle."""
    words = form.split()
    if len(words) <= SHINGLE_WORDS:
        return frozenset([form]) if form else frozenset()
    return frozenset(" ".join(words[i : i + SHINGLE_WORDS]) for i in range(len(words) - SHINGLE_WORDS + 1))
