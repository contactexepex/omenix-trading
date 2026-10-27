"""The shapes a clustering comparison counts (NP3c). Pure and counts-only: nothing here holds, returns or prints a key,
a title, a URL, a symbol or a company name. Used to compare clustering algorithm version 1 with version 2 over the same
articles before anyone switches the scheduled run."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass

from fno.ingestion.news.article.article_file import Article
from fno.ingestion.news.cluster.cluster import Clustering
from fno.ingestion.news.tagging.tagger import HIGH, Tagger

SIZE_BUCKETS = ((2, 2), (3, 5), (6, 10), (11, 10**9))  # clusters of two, three to five, six to ten, eleven or more
COMPANY_THRESHOLDS = (1, 5, 20)  # companies with at least this many tagged articles


@dataclass(frozen=True)
class Shape:
    clusters: int
    singletons: int
    largest: int
    sizes: tuple[int, ...]  # clusters per size bucket, in SIZE_BUCKETS order


@dataclass(frozen=True)
class Crossing:
    merged_by_second: int  # clusters of the second that hold articles the first kept in different clusters
    split_by_second: int  # clusters of the first whose articles the second put in different clusters


@dataclass(frozen=True)
class Coverage:
    articles: int
    tagged: int  # articles that name at least one company (title, else summary)
    tagged_high: int  # of those, exactly one company, primary (high confidence)
    companies_with_at_least: tuple[int, ...]  # companies seen in at least COMPANY_THRESHOLDS articles, in order


def shape_of(clustering: Clustering) -> Shape:
    sizes = [len(c.member_keys) for c in clustering.clusters]
    return Shape(
        len(sizes),
        sizes.count(1),
        max(sizes, default=0),
        tuple(sum(low <= n <= high for n in sizes) for low, high in SIZE_BUCKETS),
    )


def _cluster_of(clustering: Clustering) -> dict[str, int]:
    return {key: index for index, c in enumerate(clustering.clusters) for key in c.member_keys}


def crossing(first: Clustering, second: Clustering) -> Crossing:
    """Over the articles both clusterings hold (they are given the same articles, so normally all of them)."""
    in_first, in_second = _cluster_of(first), _cluster_of(second)
    shared = in_first.keys() & in_second.keys()
    return Crossing(_spanning(shared, in_second, in_first), _spanning(shared, in_first, in_second))


def _spanning(shared: Iterable[str], group_of: dict[str, int], other_of: dict[str, int]) -> int:
    """Groups of `group_of` whose shared articles lie in more than one group of `other_of`."""
    spread: dict[int, set[int]] = {}
    for key in shared:
        spread.setdefault(group_of[key], set()).add(other_of[key])
    return sum(len(groups) > 1 for groups in spread.values())


def coverage(articles: Iterable[Article], tagger: Tagger) -> Coverage:
    seen: Counter[str] = Counter()
    total = tagged = high = 0
    for article in articles:
        total += 1
        tag = tagger.tag(article.title, article.summary, article.source)
        if tag.symbols:
            tagged += 1
            seen.update(tag.symbols)
        high += tag.confidence == HIGH
    return Coverage(total, tagged, high, tuple(sum(n >= t for n in seen.values()) for t in COMPANY_THRESHOLDS))
