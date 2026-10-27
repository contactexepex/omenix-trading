"""A feed item's time (P2b): RFC 822 (RSS) and RFC 3339 (Atom, RDF dates). Never an age check. A time with no zone is
read as UTC and flagged; one that cannot be read, overflows, or has an implausible year is no time (the item is kept and
counts from when it was first seen)."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

PUBLISHED, ASSUMED_UTC, SEEN = "published", "assumed_utc", "seen"  # the item's `time_source`
PLAUSIBLE_YEARS = range(1990, 2101)
# RFC 822 reads "01 Jan 0001", a feed's minimum-date default, as 2001, so on that path (only) the year as written is checked.
YEAR_WORDS = re.compile(r"(?<![+\-:\d])\d{4}(?![\d:])")  # a four-digit year, not a zone offset like +0530


def _rfc822(text: str) -> datetime | None:
    moment = parsedate_to_datetime(text)
    if any(int(year) not in PLAUSIBLE_YEARS for year in YEAR_WORDS.findall(text)):
        raise ValueError("implausible year")
    return moment


def _read(text: str) -> tuple[datetime, bool] | None:
    """(the moment in UTC, whether its zone was assumed) or None. The conversion is inside the try: it overflows near
    year 1 and year 9999 (for example `00010101T000000+0500`, which has no standalone year to check)."""
    for read in (_rfc822, datetime.fromisoformat):
        try:
            moment = read(text)
            assumed = moment.tzinfo is None
            return (moment.replace(tzinfo=UTC) if assumed else moment).astimezone(UTC), assumed
        except (ValueError, TypeError, IndexError, OverflowError):
            continue
    return None


def parse_time(text: str) -> tuple[datetime | None, str]:
    """(the time in UTC or None, its `time_source`)."""
    text = (text or "").strip()
    found = _read(text) if text else None
    if found is None or found[0].year not in PLAUSIBLE_YEARS:
        return None, SEEN
    moment, assumed = found
    return moment, ASSUMED_UTC if assumed else PUBLISHED
