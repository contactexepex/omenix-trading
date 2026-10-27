"""One staged poll into articles (P2b1): the parser, the item checks and the article builder together, as one pure
function. The counts it returns are what the writer's per-poll reconciliation starts from: items = articles +
rejected, always."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime

from fno.ingestion.news import codes
from fno.ingestion.news.article.article_file import Article, build_article
from fno.ingestion.news.article.item_checks import item_refusal
from fno.ingestion.news.article.parse_feed import parse_poll


@dataclass(frozen=True)
class PollReading:
    articles: tuple[Article, ...]
    rejected: Counter  # fixed code -> number of items

    @property
    def items(self) -> int:
        return len(self.articles) + sum(self.rejected.values())


def read_poll(data: bytes, kind: str, seen_at: datetime) -> PollReading:
    """PollRejected(code) when the whole poll is refused; otherwise every item either an article or counted by its
    code."""
    articles, rejected = [], Counter()
    for item in parse_poll(data):
        code = item_refusal(item)
        if code:
            rejected[code] += 1
            continue
        try:
            articles.append(build_article(kind, item, seen_at))
        except (ValueError, OverflowError):
            # a link that will not parse (a bad port, a broken IPv6 host) costs this item only, never the others
            rejected[codes.ITEM_UNREADABLE] += 1
    return PollReading(tuple(articles), rejected)
