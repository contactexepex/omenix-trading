"""The tagger (NP5a; NP0 section 2g): which of the owner's companies an article is about. Pure; computed when an article
is read, never stored. Rules ported from agentic's tagger unless marked mine:

1. **Headline first.** The title is the subject: companies named in the title are tagged and the summary is not used.
Only when the title names none is the PLAIN-TEXT summary used (tags, URLs, domains and the trailing outlet name
removed). A search query that found the item never tags it. 2. **Roles.** A company named in the title is `primary`,
except where the title is a comparison ("X vs Y", "versus", "v/s") or lists companies ("A, B and C rise"; comma or
slash separated), where they are `mentioned`. Mine: a list needs at least two companies in the title, so "A, the
largest lender, rises" keeps A primary. A company found only in the summary is `mentioned`. 3. **Confidence.** `high`
when the title names exactly one company and it is primary; `low` for any other tagged item; `""` when nothing is
tagged. 4. A name matches only as whole words in any case; a symbol only in brackets and in capitals (`(SYM1)`,
`(SYM1:NSE)`, `(NSE: SYM1)`); a company's own exclusions are removed from consideration first (a hit inside an
excluded phrase does not count).

Not ported (stated in the NP5 plan): agentic's "actor" rules for brokers acting on other companies. Every text any
pattern sees is cut to `MAX_TEXT` characters (`text.py`)."""

from __future__ import annotations

import re
from dataclasses import dataclass

from fno.ingestion.news.tagging.dictionary import NameDictionary
from fno.ingestion.news.tagging.text import MAX_TEXT, capped, plain_text, spans, words

HIGH, LOW, NONE = "high", "low", ""
_VERSUS = re.compile(r"\b(?:vs\.?|versus|v/s)(?=\s|$)", re.IGNORECASE)
# a list is comma- or slash-separated; ";" separates clauses, not items
_LIST_AFTER = re.compile(r"^(?:'s)?\s*[,/]")
_LIST_BEFORE = re.compile(r"(?:[,/]\s*|,[^,:;]{1,60}\s(?:and|&)\s*)$", re.IGNORECASE)


@dataclass(frozen=True)
class Hit:
    symbol: str
    start: int
    end: int


@dataclass(frozen=True)
class Tag:
    primary: tuple[str, ...] = ()
    mentioned: tuple[str, ...] = ()
    confidence: str = NONE

    @property
    def symbols(self) -> tuple[str, ...]:
        return tuple(sorted({*self.primary, *self.mentioned}))


class Tagger:
    def __init__(self, dictionary: NameDictionary):
        self.dictionary = dictionary

    def hits(self, text: str) -> list[Hit]:
        """Every company named in `text` (at most `MAX_TEXT` characters of it), in order, exclusions applied."""
        text = text[:MAX_TEXT]
        found = self._named(text) + self._bracketed(text)
        found.sort(key=lambda hit: (hit.start, hit.end))
        return [hit for hit in found if not self._excluded(hit, text)]

    def tag(self, title: str | None, summary: str | None = None, source: str | None = None) -> Tag:
        title_text = capped(title)
        in_title = self.hits(title_text)
        if in_title:
            return self._from_title(title_text, in_title)
        in_summary = sorted({hit.symbol for hit in self.hits(plain_text(summary, source))})
        return Tag((), tuple(in_summary), LOW) if in_summary else Tag()

    # ---- title ---------------------------------------------------------------------------------------------------
    def _from_title(self, title: str, hits: list[Hit]) -> Tag:
        symbols = sorted({hit.symbol for hit in hits})
        if len(symbols) == 1:
            return Tag((symbols[0],), (), HIGH)
        if _VERSUS.search(title):
            return Tag((), tuple(symbols), LOW)
        listed = {hit.symbol for hit in hits if self._in_list(title, hit)}
        primary = tuple(s for s in symbols if s not in listed)
        return Tag(primary, tuple(s for s in symbols if s in listed), LOW)

    @staticmethod
    def _in_list(text: str, hit: Hit) -> bool:
        return bool(_LIST_AFTER.match(text[hit.end :]) or _LIST_BEFORE.search(text[: hit.start]))

    # ---- finding names -------------------------------------------------------------------------------------------
    def _named(self, text: str) -> list[Hit]:
        """The longest dictionary name at each word, left to right, never overlapping."""
        found, tokens, i = [], words(text), 0
        while i < len(tokens):
            for length in range(min(self.dictionary.longest, len(tokens) - i), 0, -1):
                symbol = self.dictionary.names.get(tuple(word for word, _, _ in tokens[i : i + length]))
                if symbol:
                    found.append(Hit(symbol, tokens[i][1], tokens[i + length - 1][2]))
                    i += length
                    break
            else:
                i += 1
        return found

    def _bracketed(self, text: str) -> list[Hit]:
        return [Hit(s, a, b) for s, a, b in self.dictionary.bracketed_symbols(text) if s in self.dictionary.symbols]

    def _excluded(self, hit: Hit, text: str) -> bool:
        return any(
            start <= hit.start and hit.end <= end
            for pattern in self.dictionary.exclusions.get(hit.symbol, ())
            for start, end in spans(pattern, text)
        )
