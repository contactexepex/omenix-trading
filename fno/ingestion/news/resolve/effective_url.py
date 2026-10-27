"""The source URL of an article (NP5b; NP6a): the resolution file's for a Google News item, the item's own https
link for a publisher item, else "". Never from feed text, a label or a page (judge 94 B1)."""

from __future__ import annotations

from fno.ingestion.news.article.article_file import Article
from fno.ingestion.news.resolve.resolution_file import Resolution


def effective_url(article: Article, resolution: Resolution | None) -> str:
    return resolution.url if resolution else article.canonical_url
