"""What a poll's answer is, as a fixed code (P2, N11): a feed, a refusal, a failure or a block page. A redirect, or a
200 that is not a feed (no feed root element: a consent, CAPTCHA or "sorry" page), is a block, never a parse failure
that would be asked again in a loop."""

from __future__ import annotations

from fno.ingestion.news import codes
from fno.shared.nse_pacer import REFUSAL_STATUS_CODES

FEED_ROOTS = (b"<rss", b"<feed", b"<rdf:rdf")
HEAD_BYTES = 4096
REDIRECTS = range(300, 400)


def classify(status: int, is_redirect: bool, content: bytes) -> str:
    """`codes.FETCHED` when the answer is a feed; otherwise the code of what it is."""
    if is_redirect or status in REDIRECTS:
        return codes.BLOCK_PAGE
    if status in REFUSAL_STATUS_CODES:
        return codes.REFUSED
    if status != 200:
        return codes.FETCH_FAILED
    head = content[:HEAD_BYTES].lower()
    return codes.FETCHED if any(root in head for root in FEED_ROOTS) else codes.BLOCK_PAGE
