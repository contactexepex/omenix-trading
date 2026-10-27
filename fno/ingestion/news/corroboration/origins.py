"""Independent origins of one cluster (NP6b; NP0 section 2i). Pure: the same views in any order give the same result,
and nothing is stored (the count depends on rule files, resolutions and read files that change after a cluster file is
closed). Articles of one agency are one origin, and so are the articles of one outlet. A copy test across outlets
(agentic's MinHash) is not ported, so two outlets copying a non-agency story count twice: `origins_unverified` and the
read counts say how far to trust a number. A wire named only by the title does not verify (a title attribution is a
heuristic)."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from fno.ingestion.news.corroboration.flags import cluster_flags, was_read
from fno.ingestion.news.corroboration.model import LABEL_OUTLET, LABEL_WIRE, Corroboration, OriginGroup
from fno.ingestion.news.origins.origin import TITLE
from fno.ingestion.news.view import ArticleView


def label_of(view: ArticleView) -> str:
    return f"{LABEL_WIRE}{view.wire}" if view.wire else f"{LABEL_OUTLET}{view.outlet}"


def countable(view: ArticleView) -> bool:
    """Can it count as an origin: from a listed outlet, not promotional, not opinion."""
    return view.listed and not view.promotional and not view.opinion


def verifies(view: ArticleView) -> bool:
    """A countable article proves its origin when its page was read or its agency has evidence other than the title."""
    return countable(view) and (was_read(view) or (bool(view.wire) and view.wire_via != TITLE))


def _group(label: str, views: list[ArticleView]) -> OriginGroup:
    return OriginGroup(
        label,
        tuple(sorted(v.key for v in views)),
        any(countable(v) for v in views),
        any(verifies(v) for v in views),
    )


def corroborate(views: Iterable[ArticleView], rules_version: str = "") -> Corroboration:
    members = list(views)
    by_label: dict[str, list[ArticleView]] = defaultdict(list)
    for view in members:
        by_label[label_of(view)].append(view)
    groups = tuple(_group(label, by_label[label]) for label in sorted(by_label))
    independent = sum(g.verified for g in groups)
    unverified = sum(g.countable and not g.verified for g in groups)
    reads = sum(v.access != "" for v in members)
    return Corroboration(
        groups, independent, unverified, cluster_flags(members, independent, unverified), reads, rules_version
    )
