"""The name dictionary (NP5a): the injected company list, turned into what the tagger looks words up in. A name or an
alias is a tuple of words (`text.word_tuple`), looked up whole, so a name matches only as whole words, in any case,
and never inside a longer word. The owner's exclusions are compiled with the safe pattern grammar (they were checked
when the list was read; a pattern that no longer compiles is dropped here rather than stop tagging). Nothing is
requested, written or printed: the dictionary is a view of a `CompanyListSource` and is rebuilt from it."""

from __future__ import annotations

import re

from fno.ingestion.news.companies.model import CompanyList, CompanyListSource
from fno.ingestion.news.safe_pattern import compile_safe
from fno.ingestion.news.tagging.text import word_tuple

_BRACKETS = re.compile(r"\(([^()]{1,40})\)")
EXCHANGES = frozenset({"NSE", "BSE"})  # a label in `(BSE: 500325)`, never the symbol beside it


class NameDictionary:
    def __init__(self, companies: CompanyList):
        self.version = companies.version
        self.names: dict[tuple[str, ...], str] = {}  # whole-word name or alias -> symbol
        self.symbols: frozenset[str] = frozenset(c.symbol for c in companies.companies)
        self.exclusions: dict[str, tuple[re.Pattern, ...]] = {}
        for company in companies.companies:
            for text in (company.name, *company.aliases):
                key = word_tuple(text)
                if key:
                    self.names.setdefault(key, company.symbol)
            compiled = tuple(p for p in (_compiled(e) for e in company.exclusions) if p is not None)
            if compiled:
                self.exclusions[company.symbol] = compiled
        self.longest = max((len(key) for key in self.names), default=0)

    @classmethod
    def from_source(cls, source: CompanyListSource) -> NameDictionary:
        return cls(source.companies())

    @staticmethod
    def bracketed_symbols(text: str) -> list[tuple[str, int, int]]:
        """(symbol, start, end) for each `(SYM)`, `(SYM:NSE)` or `(NSE: SYM)`; case-sensitive."""
        found = []
        for match in _BRACKETS.finditer(text):
            parts = [part.strip() for part in match.group(1).split(":")]
            if len(parts) <= 3:  # `SYM`, `SYM:EXCHANGE`, `EXCHANGE: SYM`; kept by the tagger only if a symbol
                found += [(p, match.start(), match.end()) for p in _candidates(parts)]
        return found


def _candidates(parts: list[str]) -> list[str]:
    """The parts that may be a symbol: an exchange label next to another part is a label (`(BSE: 500325)` is not the
    company BSE); a lone `(BSE)` is a symbol, and in `(NSE: BSE)` the first part is the label."""
    if len(parts) == 1:
        return [p for p in parts if p]
    if len(parts) == 2 and parts[0] in EXCHANGES:
        return [parts[1]] if parts[1] else []
    return [p for p in parts if p and p not in EXCHANGES]


def _compiled(pattern: str) -> re.Pattern | None:
    try:
        return compile_safe(pattern)
    except ValueError:
        return None
