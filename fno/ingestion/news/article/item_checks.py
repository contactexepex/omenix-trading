"""What an item must have to be recorded (P2b): a title, and a link or a guid, none of it absurdly long. Returns the
fixed code of the first failure, or None. There is no age or time check: an item without a usable time is still
recorded."""

from __future__ import annotations

from dataclasses import astuple

from fno.ingestion.news import codes
from fno.ingestion.news.article.raw_item import RawItem

MAX_FIELD_CHARS = 20_000


def item_refusal(item: RawItem) -> str | None:
    if not item.title.strip():
        return codes.ITEM_MISSING_TITLE
    if not (item.link.strip() or item.guid.strip()):
        return codes.ITEM_MISSING_LINK
    if any(len(field) > MAX_FIELD_CHARS for field in astuple(item)):
        return codes.ITEM_TOO_LONG
    return None
