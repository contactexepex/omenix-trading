"""The id of a planned feed (NP3b; NP3 plan section 4, judge 77 F1 and F5). It is derived from the feed's own content so
the same query always has the same id however the list is reordered or extended, and a different query can never take
it. It is keyed with the feed list's private salt (HMAC-SHA-256): feed ids are committed publicly in the poll log, so an
unsalted hash would let anyone hash a company name and confirm the owner watches it. The salt and `normalise_query` are
FROZEN: changing either would change every id and orphan every staged poll."""

from __future__ import annotations

import hashlib
import hmac

ID_PREFIX = "q-"
ID_HEX_LENGTH = 8


def normalise_query(query: str) -> str:
    """Case and runs of spaces do not make a different query."""
    return " ".join(query.split()).casefold()


def planned_feed_id(salt: str, kind: str, query: str) -> str:
    message = f"{kind}\0{normalise_query(query)}".encode()
    digest = hmac.new(salt.encode(), message, hashlib.sha256).hexdigest()
    return ID_PREFIX + digest[:ID_HEX_LENGTH]
