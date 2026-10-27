"""What a feed item said, as text (P2b): the parser's output before any check or key."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RawItem:
    title: str = ""
    link: str = ""
    guid: str = ""
    published: str = ""  # the time as written; read by `times.parse_time`
    summary: str = ""
    source: str = ""  # the outlet's name, where the item names one
    source_url: str = ""  # the `url` of the item's <source> element (Google News: the outlet's home page)
