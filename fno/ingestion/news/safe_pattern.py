"""The one pattern grammar for every pattern the owner writes or the repository ships (NP3a for exclusions, NP5 for
promotional phrases and material terms): a small allow-list, not a list of refused shapes, because no list of refused
shapes is complete (measured: two `.*` took 14 s on 5,000 characters). A safe pattern is plain text, up to
`MAX_GROUPS` `(?:A|B)` groups of plain text, at most `MAX_OPTIONALS` optional letters (`x?`) and one trailing `\\w*`.
Plain text is letters, digits, space and `& ' - # / :` plus the escaped `\\.`, `\\(` and `\\)` (judge 90 widened it by
these literals so the shipped phrases fit; literals add no ambiguity, so the bounds that make matching safe are
untouched). Nothing else is accepted: no `.`, `*`, `+`, `{n,m}`, class, look-around or back-reference."""

from __future__ import annotations

import re

MAX_PATTERN = 120
MAX_OPTIONALS, MAX_GROUPS = 4, 2  # each `x?` doubles the ways to match, each group multiplies them by its alternatives
_LETTER = r"(?:[A-Za-z0-9 &'#/:-]|\\[.()])"  # a plain character, or an escaped full stop or parenthesis
_ATOM = _LETTER + r"\??"  # a letter, optionally absent (`Lifespaces?`)
_SEQUENCE = f"(?:{_ATOM})+"
_GROUP = rf"\(\?:{_SEQUENCE}(?:\|{_SEQUENCE})*\)"  # (?:Alpha|Beta): alternatives of plain text, no quantifier after it
SAFE_PATTERN = re.compile(rf"(?:{_ATOM}|{_GROUP})+(?:\\w\*)?")  # and at most one word tail, last


def is_safe_pattern(pattern: str) -> bool:
    """True when the pattern is in the grammar and within its bounds (not yet known to compile: `compile_safe`)."""
    return (
        len(pattern) <= MAX_PATTERN
        and SAFE_PATTERN.fullmatch(pattern) is not None
        and pattern.count("?") <= MAX_OPTIONALS
        and pattern.count("(?:") <= MAX_GROUPS
    )


def compile_safe(pattern: str) -> re.Pattern:
    """The compiled, case-insensitive pattern; ValueError when it is not safe or does not compile."""
    if not is_safe_pattern(pattern):
        raise ValueError("not a safe pattern")
    try:
        return re.compile(pattern, re.IGNORECASE)
    except re.error:
        raise ValueError("not a safe pattern") from None
