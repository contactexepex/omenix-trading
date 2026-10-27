"""In what order the read pass takes articles (NP8): a strategy behind the pass. `NewestFirst` is what the pass always
did (it keeps its own code path); `MaterialFirst` ranks the newest articles in two tiers, the material ones first and
newest first inside each tier (the input is newest first and the partition is stable, so the ranking is
deterministic). An article is material when the owner's terms weigh its title at 1 or more AND the title names exactly
one company with high confidence (NP5b). The summary plays no part: a company named only in a summary is never high
confidence."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass

from fno.ingestion.news.materiality.terms import MaterialTerms
from fno.ingestion.news.tagging.tagger import Tagger

NEWEST_FIRST, MATERIAL_FIRST = "newest_first", "material_first"


@dataclass(frozen=True)
class Scored:
    key: str
    title: str
    source: str
    link: str  # the article's own https link ("" for a Google News item, whose page comes from its resolution file)
    wrapper: bool


class ReadOrder(ABC):
    name = ""

    @abstractmethod
    def rank(self, scored: Sequence[Scored]) -> tuple[list[Scored], int]:
        """(the articles in reading order, how many of them are material); `scored` is newest first."""


class NewestFirst(ReadOrder):
    name = NEWEST_FIRST

    def rank(self, scored: Sequence[Scored]) -> tuple[list[Scored], int]:
        return list(scored), 0


class MaterialFirst(ReadOrder):
    name = MATERIAL_FIRST

    def __init__(self, tagger: Tagger, terms: MaterialTerms):
        self.tagger, self.terms = tagger, terms

    def material(self, article: Scored) -> bool:
        tag = self.tagger.tag(article.title, None, article.source)
        return self.terms.is_material(article.title, tag, article.source)

    def rank(self, scored: Sequence[Scored]) -> tuple[list[Scored], int]:
        flags = [self.material(article) for article in scored]
        first = [a for a, material in zip(scored, flags, strict=True) if material]
        rest = [a for a, material in zip(scored, flags, strict=True) if not material]
        return first + rest, len(first)
