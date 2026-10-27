"""Vendor and promotional content (NP5b; NP0 section 2g): `PromotionalFilter` flags an article as promotional when its
provider, byline or source label is a listed promotional provider, its outlet is a listed promotional domain, or its
title or cleaned summary carries one of the shipped marker phrases. Such an article is never counted as an independent
origin. The providers, domains and phrases are the PUBLIC rules in `config/news_sources.yaml`; the phrases are in the
safe pattern grammar (the source-rule loader refuses any that is not) and run against at most `MAX_TEXT` characters."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from fno.ingestion.news.sources.rules import SourceRules
from fno.ingestion.news.tagging.text import capped, plain_text

PROVIDER, DOMAIN, PHRASE = "provider", "domain", "phrase"


@dataclass(frozen=True)
class Promotion:
    promotional: bool = False
    via: str = ""


class PromotionalFilter:
    def __init__(self, rules: SourceRules):
        from fno.ingestion.news.safe_pattern import compile_safe

        self.rules = rules
        self.phrases = tuple(compile_safe(p) for p in rules.promotional.text)

    def check(
        self,
        host: str | None,
        provider: str | None,
        authors: Iterable[str],
        source_label: str | None,
        title: str | None,
        summary: str | None,
    ) -> Promotion:
        if any(self.rules.is_promotional_provider(name) for name in (provider, source_label, *authors)):
            return Promotion(True, PROVIDER)
        if self.rules.is_promotional_domain(host):
            return Promotion(True, DOMAIN)
        texts = (capped(title), plain_text(summary, source_label))
        if any(phrase.search(text) for phrase in self.phrases for text in texts):
            return Promotion(True, PHRASE)
        return Promotion()
