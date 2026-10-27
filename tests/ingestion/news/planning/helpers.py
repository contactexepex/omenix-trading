"""Hand-made inputs for the NP3b tests: invented hosts, queries and company names only."""

from __future__ import annotations

import json

from fno.ingestion.news.companies.model import Company, CompanyList
from fno.ingestion.news.planning.discovery import parse_discovery

SALT = "s" * 32
SEARCH_URL = "https://search.svc.example/rss/search"


def discovery_document(**changes) -> dict:
    document = {
        "format": 1,
        "search": {"url": SEARCH_URL, "query_param": "q", "params": {"hl": "en", "gl": "XX"}},
        "broad": ["zzmarket outlook", "Zzsector news"],
        "targeted_template": "{name} zzstock",
        "publisher_feeds": [{"id": "feed-01", "url": "https://feeds.pub.example/rss"}],
    }
    document.update(changes)
    return document


def discovery(**changes):
    return parse_discovery(json.dumps(discovery_document(**changes)).encode(), 1)


def company(symbol: str, name: str, targeted: bool = False) -> Company:
    return Company(symbol, name, targeted=targeted)


def companies(*entries: Company) -> CompanyList:
    return CompanyList(1, tuple(entries))
