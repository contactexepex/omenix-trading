"""The title form two articles are compared on (P2c): lower-case, punctuation and a trailing outlet name removed, then
word shingles. Pure text work: nothing here reads a store, a clock or the network, and nothing is logged.
"""

from __future__ import annotations

import re

SEPARATORS = (" - ", " – ", " — ", " | ")
MAX_OUTLET_WORDS = 4  # "Economic Times", "The Hindu BusinessLine": a longer tail is part of the headline
MIN_HEADLINE_WORDS = 3  # a title this short is never trimmed: "Budget - Live" is not an outlet name
SHINGLE_WORDS = 2
NOT_WORD = re.compile(r"[\W_]+")


def _without_outlet(title: str) -> str:
    cut = max(title.rfind(separator) for separator in SEPARATORS)
    if cut < 0:
        return title
    head, tail = title[:cut], title[cut:].strip(" -–—|")
    long_enough = len(NOT_WORD.sub(" ", head).split()) >= MIN_HEADLINE_WORDS
    return head if long_enough and 0 < len(tail.split()) <= MAX_OUTLET_WORDS else title


def title_form(title: str) -> str:
    return NOT_WORD.sub(" ", _without_outlet(title).casefold()).strip()


def shingles(form: str) -> frozenset[str]:
    """Overlapping word groups; a one-word title is its own single shingle."""
    words = form.split()
    if len(words) <= SHINGLE_WORDS:
        return frozenset([form]) if form else frozenset()
    return frozenset(" ".join(words[i : i + SHINGLE_WORDS]) for i in range(len(words) - SHINGLE_WORDS + 1))
