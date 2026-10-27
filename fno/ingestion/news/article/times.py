"""A feed item's time (P2b): RFC 822 (RSS) and RFC 3339 (Atom, RDF dates). Never an age check. A time with no zone is
read as UTC and flagged; one that cannot be read is no time (the item then counts from when it was first seen)."""

from __future__ import annotations

from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

PUBLISHED, ASSUMED_UTC, SEEN = "published", "assumed_utc", "seen"  # the item's `time_source`


def parse_time(text: str) -> tuple[datetime | None, str]:
    """(the time in UTC or None, its `time_source`)."""
    text = (text or "").strip()
    if not text:
        return None, SEEN
    for read in (parsedate_to_datetime, datetime.fromisoformat):
        try:
            moment = read(text)
        except (ValueError, TypeError, IndexError, OverflowError):
            continue
        if moment.tzinfo is None:
            return moment.replace(tzinfo=UTC), ASSUMED_UTC
        return moment.astimezone(UTC), PUBLISHED
    return None, SEEN
