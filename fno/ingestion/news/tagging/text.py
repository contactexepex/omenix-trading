"""Text for tagging (NP5a): cleaning a summary to plain text, folding it, cutting it to a fixed length and splitting
it into words with their positions. Pure and bounded: a feed summary is untrusted and uncapped, so it is cut to
`MAX_RAW` characters before the cleaners run and to `MAX_TEXT` characters after them, and every pattern the tagger
runs sees at most `MAX_TEXT`. That is the hard time bound the pattern grammar leans on (judge 78, judge 79)."""

from __future__ import annotations

import html
import re
from collections.abc import Iterator

MAX_RAW = 20_000  # of a summary, before cleaning (the cleaners are linear except the bare-domain one)
MAX_TEXT = 1_000  # of a title or of a CLEANED summary: what any pattern is run against

_TAGS = re.compile(r"<[^<>]*>")  # never reads past the next "<", so a run of them is not quadratic
_URLS = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)
_DOMAINS = re.compile(  # bounded labels and count: a long run of "a.a.a." is linear, not quadratic
    r"\b(?:[a-z0-9-]{1,63}\.){1,5}(?:com|in|org|net|co|io|uk|us|news|biz|info)\b(?:/\S*)?", re.IGNORECASE
)
_QUOTES = str.maketrans({"’": "'", "‘": "'", " ": " "})
_WORD = re.compile(r"[\w&']+")
_POSSESSIVE = re.compile(r"'s?$")  # "Acme's" and "banks'" are the name, not another word
_SEPARATORS = " -–—|"


def fold(text: str) -> str:
    """Typographic quotes and no-break spaces folded to plain ones."""
    return text.translate(_QUOTES)


def plain_text(summary: str | None, source: str | None = None) -> str:
    """A summary as plain text: HTML tags, entities, URLs and bare domains removed (a Google News summary links its own
    host, which once tagged nearly everything), runs of space collapsed, the trailing outlet name dropped, then cut to
    `MAX_TEXT`. A link or a source name never becomes a company."""
    text = fold(html.unescape(_TAGS.sub(" ", (summary or "")[:MAX_RAW])))
    text = re.sub(r"\s+", " ", _DOMAINS.sub(" ", _URLS.sub(" ", text))).strip()
    name = fold(source or "").strip()
    if name and text.lower().endswith(name.lower()):
        text = text[: -len(name)].rstrip(" -|")
    return text[:MAX_TEXT]


def capped(title: str | None) -> str:
    return fold(title or "")[:MAX_TEXT]


def without_outlet(title: str, source: str | None) -> str:
    """A title without a trailing " - Outlet" or " | Outlet" naming the source (Google News adds it), so the outlet's
    own name never tags. Only after a separator: a title that ends in the source's name as a word keeps it."""
    name = fold(source or "").strip()
    if name and title.lower().endswith(name.lower()):
        head = title[: -len(name)]
        if head.rstrip() != head and head.rstrip().endswith(tuple(_SEPARATORS.strip())):
            return head.rstrip(_SEPARATORS)
    return title


def words(text: str) -> list[tuple[str, int, int]]:
    """(lower-case word, start, end): letters, digits, `_`, `&` and an apostrophe, so `L&T` stays whole;
    a trailing `'s` or `'` is dropped (on names and on text alike), so "Acme's" is "acme"."""
    found = []
    for match in _WORD.finditer(text):
        word = _POSSESSIVE.sub("", match.group().lower())
        if word:
            found.append((word, match.start(), match.start() + len(word)))
    return found


def word_tuple(text: str) -> tuple[str, ...]:
    """The words of a name, for the dictionary."""
    return tuple(word for word, _, _ in words(fold(text)))


def spans(pattern: re.Pattern, text: str) -> Iterator[tuple[int, int]]:
    for match in pattern.finditer(text):
        yield match.start(), match.end()
