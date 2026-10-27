"""The news session's per-run pacer (NP3b): built from the private feed list, so no host name is written in code. A host
that serves search feeds (kind `wrapper`) is asked at most once every 1.5 seconds; every other host keeps the default of
one a second. `fno/shared/nse_pacer.py` is not touched: its NSE table is the default only when no table is given, and
the news session always gives its own."""

from __future__ import annotations

from fno.ingestion.news.article.keys import WRAPPER
from fno.ingestion.news.feeds import FeedList
from fno.shared.nse_pacer import NsePacer

WRAPPER_SPACING_SECONDS = 1.5


def pacer_for(feeds: FeedList) -> NsePacer:
    return NsePacer(spacing={f.host: WRAPPER_SPACING_SECONDS for f in feeds.feeds if f.kind == WRAPPER})
