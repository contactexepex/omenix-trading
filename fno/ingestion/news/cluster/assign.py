"""The assignment rule (P2c; design R6; NP6a), explicit and non-chaining: articles are taken in order of (story time,
key). Version 2 first tries the identity URL: an article whose URL (see `url_identity.py`) was taken by an earlier
member of a cluster joins THAT cluster, whichever member it is (identity is transitive, so this cannot chain by
score), and one URL belongs to the cluster that took it first. Otherwise, and always in version 1, it joins the first
existing cluster whose ANCHOR (its earliest member) it matches by title, never any other member, else it starts a new
cluster. Clusters are created in anchor order, so "the first" is the earlier anchor and, on equal times, the smaller
key. An article that matches two anchors joins the earlier and the two clusters are not merged, which is what keeps
A~B and B~C from putting A and C together.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from fno.ingestion.news.cluster.matcher import Matcher, Prepared


@dataclass(frozen=True)
class Assignment:
    clusters: list[list[Prepared]]
    url_joins: int = 0  # articles put in a cluster by their URL
    url_joins_unlike_title: int = 0  # of those, the ones the title rule would not have put with the anchor


def assign(articles: Iterable[Prepared], matcher: Matcher) -> Assignment:
    clusters: list[list[Prepared]] = []
    owner: dict[str, tuple[int, Prepared]] = {}  # identity URL -> (cluster, the member that took it first)
    joins = unlike = 0
    for article in sorted(articles, key=lambda a: a.order):
        index = _by_url(article, owner, matcher)
        if index is not None:
            joins += 1
            unlike += not matcher.same_story(clusters[index][0], article)
        else:
            index = _by_title(clusters, article, matcher)
        if index is None:
            clusters.append([article])
            index = len(clusters) - 1
        else:
            clusters[index].append(article)
        if article.url:
            owner.setdefault(article.url, (index, article))
    return Assignment(clusters, joins, unlike)


def _by_url(article: Prepared, owner: dict[str, tuple[int, Prepared]], matcher: Matcher) -> int | None:
    taken = owner.get(article.url) if article.url else None
    return taken[0] if taken and matcher.same_url(taken[1], article) else None


def _by_title(clusters: list[list[Prepared]], article: Prepared, matcher: Matcher) -> int | None:
    return next((i for i, members in enumerate(clusters) if matcher.same_story(members[0], article)), None)
