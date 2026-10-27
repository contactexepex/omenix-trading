"""The article file (P2, D4): fixed fields only, as deterministic JSON bytes, so the same article always gives the same
bytes. A later copy is compared on the fixed fields WITHOUT `first_seen_at` (and with no feed id at all): identical
is a true no-op, different is a revision. The title, summary and URL live only in this private Drive file, never in
anything committed. A Google News item's title is stored without its trailing " - Outlet" (NP9, frozen rule in
`text_rules.py`)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime

from fno.ingestion.news.article.canonical import canonical_url
from fno.ingestion.news.article.formats import read_document
from fno.ingestion.news.article.keys import PUBLISHER, WRAPPER, item_key
from fno.ingestion.news.article.raw_item import RawItem
from fno.ingestion.news.article.source_facts import source_facts
from fno.ingestion.news.article.times import parse_time
from fno.ingestion.news.text_rules import without_outlet

FORMAT = 2  # 1: the first files; 2 adds the source facts below. Both are read (formats.py); only 2 is written.


@dataclass(frozen=True)
class Article:
    key: str
    kind: str
    source: str
    title: str
    summary: str
    canonical_url: str  # "" for a Google News item (its link is a redirect wrapper that is not resolved)
    published_at: str  # UTC ISO, "" when the item gave none
    time_source: str
    first_seen_at: str
    source_domain: str = ""  # the outlet's plain host ("" unknown); a fact, never a tier
    wrapper_link: str = ""  # a Google News item's redirect link, kept so it can be resolved later (NP2c)

    def fixed_fields(self) -> tuple:
        """What a re-poll is compared on: everything but when it was first seen."""
        return tuple(v for k, v in asdict(self).items() if k != "first_seen_at")

    def to_bytes(self) -> bytes:
        document = {"format": FORMAT, **asdict(self)}
        return json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def build_article(kind: str, item: RawItem, seen_at: datetime) -> Article:
    published, time_source = parse_time(item.published)
    link = canonical_url(item.link) if kind == PUBLISHER and item.link.strip() else ""
    facts = source_facts(kind, link, item.link, item.source_url)
    title = item.title.strip()
    if kind == WRAPPER:  # Google News appends " - Outlet"; the key above was computed from the raw item, so no revision
        title = without_outlet(title, item.source.strip()) or title  # never an empty title
    return Article(
        key=item_key(kind, item, published),
        kind=kind,
        source=item.source.strip(),
        title=title,
        summary=item.summary.strip(),
        canonical_url=link,
        published_at=published.isoformat(timespec="seconds") if published else "",
        time_source=time_source,
        first_seen_at=seen_at.isoformat(timespec="seconds"),
        source_domain=facts.domain,
        wrapper_link=facts.wrapper_link,
    )


def article_from_bytes(data: bytes) -> Article:
    """An article file of ours, of any readable format. ValueError for anything else (formats.read_document): an unknown
    or non-integer format, a missing key, an unknown extra key, text that is not JSON. A format 1 file has no source
    facts; they read as empty."""
    document = read_document(data)
    if document is None:
        raise ValueError("not an article file")
    return Article(**document[1])
