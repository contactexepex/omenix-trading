"""The page snippet (NP10; owner decision E1 = YES, 28 Oct 2026): the first few sentences of the article body, bounded
and deterministic, stored in its own field of the read file. Never the body: at most `MAX_SENTENCES` sentences and
`MAX_CHARS` characters. Pure and linear (a run of stops is matched once): the body is cut to `MAX_SCAN` characters
before the cleaners run, and the same page always gives the same snippet, so a re-read is the same file. Page text is
untrusted: it is cleaned, cut and stored, never followed."""

from __future__ import annotations

import html
import re

MAX_SENTENCES = 3
MAX_CHARS = 600
MAX_SCAN = 20_000  # of the raw body, before cleaning (tag removal is linear)
ABBREVIATIONS = frozenset(
    {"rs.", "mr.", "mrs.", "ms.", "dr.", "ltd.", "co.", "no.", "vs.", "inc.", "sr.", "jr.", "st."}
)

_TAGS = re.compile(r"<[^<>]*>")
_CONTROL = re.compile(r"[\x00-\x1f\x7f]+")
_STOP = re.compile(r"(?<![.!?।])[.!?।]++(?=\s+\S)")  # a run of stops, then space, then something follows


def clean(body: str) -> str:
    """Plain single-line text: entities unescaped, then tags removed (so an entity-encoded tag goes too), control
    characters and runs of space collapsed."""
    text = _TAGS.sub(" ", html.unescape(body[:MAX_SCAN]))  # unescape first: an encoded tag is a tag (judge 119 B1)
    return " ".join(_CONTROL.sub(" ", text).split())


def _starts_a_sentence(text: str, end: int) -> bool:
    """False before a digit or a lower-case letter ("Rs. 500", "approx. nine"), true otherwise."""
    following = text[end:].lstrip()[:1]
    return not (following.isdigit() or following.islower())


def _ends_in_abbreviation(text: str, stop: int) -> bool:
    """`stop`: where the full stop is; the word that ends with it, in lower case, is looked up whole."""
    word = text[: stop + 1].rsplit(" ", 1)[-1].lower()
    return word in ABBREVIATIONS


def sentences(text: str, limit: int = MAX_SENTENCES) -> list[str]:
    """The first `limit` sentences of clean text."""
    found, start = [], 0
    for match in _STOP.finditer(text):
        if _starts_a_sentence(text, match.end()) and not _ends_in_abbreviation(text, match.start()):
            found.append(text[start : match.end()].strip())
            start = match.end()
            if len(found) == limit:
                return found
    rest = text[start:].strip()
    return found + [rest] if rest else found


def _cut(text: str) -> str:
    """At most `MAX_CHARS`, ending at a word boundary."""
    if len(text) <= MAX_CHARS:
        return text
    head = text[:MAX_CHARS]
    return (head.rsplit(" ", 1)[0] if " " in head and text[MAX_CHARS] != " " else head).rstrip()


def summary_extract(body: str) -> str:
    return _cut(" ".join(sentences(clean(body))))
