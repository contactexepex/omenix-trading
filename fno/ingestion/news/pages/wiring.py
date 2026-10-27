"""Composition root of the page fetcher (NP4a): the only place that picks the concrete fetcher, the allowlist and the
resolver. The allowlist is the public `config/news_sources.yaml`."""

from __future__ import annotations

from collections.abc import Callable

from fno.ingestion.news.pages.fetcher import HttpsPageFetcher
from fno.ingestion.news.pages.probe import ProbeReport, probe_outlets
from fno.ingestion.news.sources.loader import load_source_rules


def build_page_fetcher(include_refusing: bool = False) -> HttpsPageFetcher:
    """The ordinary fetcher. `include_refusing`: the outlet probe alone; any LISTED host, `fetch: false` too."""
    rules = load_source_rules()
    allowed = (lambda host: rules.lookup(host) is not None) if include_refusing else None
    return HttpsPageFetcher(rules, host_allowed=allowed)


def build_outlet_probe(include_refusing: bool) -> Callable[[Callable[[str], None]], ProbeReport]:
    """The probe, as a function of where each outlet's line goes as soon as it is known."""
    rules = load_source_rules()
    return lambda on_result: probe_outlets(rules, build_page_fetcher(include_refusing), include_refusing, on_result)
