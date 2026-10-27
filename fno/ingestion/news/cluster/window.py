"""Which articles a clustering run looks at (P2c; design N6, R2). An article belongs to a run by its EFFECTIVE time
`max(published, first seen)`, so a late arrival (published three days ago, first seen today) is clustered instead of
lost; one with no usable publication time counts as published when first seen. The window limits clustering only: an
article that leaves it stays in the Record under its own id. An article dated in the future waits until the run's end
catches up with it.

**The lengths are defaults, not findings** (no real news collected yet): reasoning only, to be re-tuned from the first
week of real polls. See `similarity.py` for what that means for anything derived from clusters.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from fno.ingestion.news.article.article_file import Article

WINDOW = timedelta(hours=48)  # how far back a run looks (reasoning only, untuned)
MATCH_WINDOW = timedelta(hours=36)  # two articles further apart than this are not the same story (reasoning only)


def story_time(article: Article) -> datetime:
    """When the story was published (or, with no usable time, first seen): orders articles and picks the anchor."""
    return datetime.fromisoformat(article.published_at or article.first_seen_at)


def effective_time(article: Article) -> datetime:
    return max(story_time(article), datetime.fromisoformat(article.first_seen_at))


def in_window(article: Article, as_of: datetime) -> bool:
    return (
        as_of - WINDOW <= effective_time(article) <= as_of
    )  # effective >= first seen, so this also needs seen <= as_of
