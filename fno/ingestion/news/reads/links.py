"""One question both ways of choosing pages ask (NP8): may this page's host be requested at all."""

from __future__ import annotations

from urllib.parse import urlsplit

from fno.ingestion.news.sources.rules import SourceRules, plain_host


def fetchable(rules: SourceRules, url: str) -> bool:
    return rules.may_fetch(plain_host(urlsplit(url).hostname))
