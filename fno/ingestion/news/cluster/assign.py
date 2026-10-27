"""The assignment rule (P2c; design R6), explicit and non-chaining: articles are taken in order of (story time, key);
each joins the first existing cluster whose ANCHOR (its earliest member) it matches, never any other member, else it
starts a new cluster. Clusters are created in anchor order, so "the first" is the earlier anchor and, on equal times,
the smaller key. An article that matches two anchors joins the earlier and the two clusters are not merged, which is
what keeps A~B and B~C from putting A and C together.
"""

from __future__ import annotations

from collections.abc import Iterable

from fno.ingestion.news.cluster.matcher import Matcher, Prepared


def assign(articles: Iterable[Prepared], matcher: Matcher) -> list[list[Prepared]]:
    clusters: list[list[Prepared]] = []
    for article in sorted(articles, key=lambda a: a.order):
        for members in clusters:
            if matcher.same_story(members[0], article):
                members.append(article)
                break
        else:
            clusters.append([article])
    return clusters
