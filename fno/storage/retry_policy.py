"""How an NSE download treats each answer (story A9b): what is worth another try, how long to wait, and when to stop.

- used: 2xx; not published: 404;
- retried: no connection, a timeout or a cut answer, HTTP 429 and every 5xx, at most `len(RETRY_WAITS) + 1` tries;
  a second 429 in a row stops at once, since the pacer has just paused the host (`REFUSALS_BEFORE_PAUSE`);
- refused, never retried: 403 and every other status (retrying a refusal invites a longer block; the pacer pauses a
  host after two refusals in a row); a request that cannot be built (a bad URL) is not retried either;
- `Retry-After` on a retried answer stretches the wait; above `MAX_RETRY_AFTER_SECONDS` the download stops at once.
  Reasoning only: past two minutes NSE is blocking, not hiccuping; the pacer's 15-minute pause and the next scheduled
  run are the right retry. Worst case per file: 65 s of waits, or 3 x 120 s, plus up to 4 request timeouts; A12's
  `filings archive --max-minutes` checks its deadline before each file, so only the file in flight runs over (twice
  that for a truncated file's second download).
"""

from __future__ import annotations

from datetime import datetime
from email.utils import parsedate_to_datetime

import requests

RETRY_WAITS = (5, 15, 45)  # seconds before tries 2, 3 and 4
MAX_RETRY_AFTER_SECONDS = 120
TOO_MANY_REQUESTS, NOT_FOUND = 429, 404
OK, NOT_PUBLISHED, RETRY, REFUSED = "ok", "not published", "retry", "refused"
UNBUILDABLE = (  # a request that could never be sent: a code fault, never worth another try
    requests.exceptions.InvalidURL,
    requests.exceptions.MissingSchema,
    requests.exceptions.InvalidSchema,
    requests.exceptions.InvalidHeader,
)


def verdict(status: int) -> str:
    """What an HTTP status means for the download."""
    if 200 <= status <= 299:
        return OK
    if status == NOT_FOUND:
        return NOT_PUBLISHED
    if status == TOO_MANY_REQUESTS or 500 <= status <= 599:
        return RETRY
    return REFUSED


def retry_after_seconds(header: str | None, now: datetime) -> float | None:
    """`Retry-After` in seconds (a number or an HTTP date); None when absent, malformed or already past."""
    if not header:
        return None
    text = header.strip()
    if text.isascii() and text.isdigit():
        return float(text)
    try:
        moment = parsedate_to_datetime(text)
    except (TypeError, ValueError):
        return None
    if moment is None or moment.tzinfo is None:
        return None
    seconds = (moment - now).total_seconds()
    return seconds if seconds > 0 else None
