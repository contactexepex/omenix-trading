"""Text rules shared by the article file and the tagging (NP9). FROZEN: the stored title of a Google News item is cut
with `without_outlet`, so the rule is part of the Record's bytes. Changing it makes every re-poll inside the window
record a revision, which is a lane 1 Record change (a format bump, or a stated note that re-polls will record
revisions). It lives here, not in `tagging/`, so that tuning the tagger can never change what is stored."""

from __future__ import annotations

_QUOTES = str.maketrans({"’": "'", "‘": "'", "\u00a0": " "})
_SEPARATORS = " -–—|"


def fold(text: str) -> str:
    """Typographic quotes and no-break spaces folded to plain ones."""
    return text.translate(_QUOTES)


def without_outlet(title: str, source: str | None) -> str:
    """A title without a trailing " - Outlet" or " | Outlet" naming the source (Google News adds it), so the outlet's
    own name never tags. Only after a separator: a title that ends in the source's name as a word keeps it. The match
    is on folded text but the cut is on the title given (`fold` swaps one character for one), so quotes survive."""
    name = fold(source or "").strip()
    if name and fold(title)[-len(name) :].lower() == name.lower():
        head = title[: -len(name)]
        if head.rstrip() != head and head.rstrip().endswith(tuple(_SEPARATORS.strip())):
            return head.rstrip(_SEPARATORS)
    return title
