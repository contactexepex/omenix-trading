"""The flags of a cluster (NP6b): each fires on exactly one rule, in a fixed order. Ported from agentic's names except
`sources_say` and `duplicates_removed` (NP6 plan, "Said plainly")."""

from __future__ import annotations

from collections.abc import Sequence

from fno.ingestion.news.corroboration import model
from fno.ingestion.news.reads.read_file import FULL, PARTIAL, PAYWALLED
from fno.ingestion.news.view import ArticleView

READ_ACCESS = (FULL, PARTIAL, PAYWALLED)


def was_read(view: ArticleView) -> bool:
    return view.access in READ_ACCESS


def cluster_flags(views: Sequence[ArticleView], independent: int, unverified: int) -> tuple[str, ...]:
    checks = (
        (any(v.promotional for v in views), model.PROMOTIONAL_PROVIDER),
        (independent == 1, model.SINGLE_SOURCE),
        (independent == 0, model.NO_VETTED_ORIGIN),
        (unverified > 0, model.ORIGINS_UNVERIFIED),
        (any(v.opinion for v in views), model.OPINION),
        (not any(v.listed for v in views), model.LOW_TIER_ONLY),
        (not any(was_read(v) for v in views), model.UNREAD),
    )
    return tuple(flag for fired, flag in checks if fired)
