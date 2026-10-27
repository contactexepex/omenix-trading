"""Are two articles the same story (P2c; stages 1 and 2 of the design, the entity as a bar-mover only).

1. the same key is the same article;
2. otherwise the titles must be alike enough, and the stories published close enough in time. An entity never decides
   alone: `entities.bar_for` only moves the bar the title score must reach.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from fno.ingestion.news.article.article_file import Article
from fno.ingestion.news.cluster.entities import bar_for, entities_in
from fno.ingestion.news.cluster.similarity import Similarity
from fno.ingestion.news.cluster.title_text import shingles, title_form
from fno.ingestion.news.cluster.window import MATCH_WINDOW, story_time


@dataclass(frozen=True)
class Prepared:
    """An article with the work done once: its title form's shingles and entities, and its story time."""

    article: Article
    shingles: frozenset[str]
    entities: frozenset[str]
    story_time: datetime

    @classmethod
    def of(cls, article: Article) -> Prepared:
        form = title_form(article.title)
        return cls(article, shingles(form), entities_in(form), story_time(article))

    @property
    def order(self) -> tuple[datetime, str]:
        return self.story_time, self.article.key


class Matcher:
    def __init__(self, similarity: Similarity):
        self.similarity = similarity

    def same_story(self, a: Prepared, b: Prepared) -> bool:
        if a.article.key == b.article.key:
            return True
        if abs(a.story_time - b.story_time) > MATCH_WINDOW:
            return False
        return self.similarity.score(a.shingles, b.shingles) >= bar_for(a.entities, b.entities)
