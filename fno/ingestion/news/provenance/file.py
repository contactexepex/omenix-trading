"""The bytes of one provenance file (NP11): `{"day", "format", "pairs", "seal"}`, sorted, deterministic. Page of the
Record that only ever grows: a day file once, then numbered supplements; nothing is rewritten."""

from __future__ import annotations

import json
from datetime import date

from fno.ingestion.news.provenance.model import FORMAT, Pair, Pairs, path_of, seal_of

KEYS = frozenset({"day", "format", "pairs", "seal"})


def to_bytes(day: date, number: int, salt: str, pairs: Pairs) -> bytes:
    document = {
        "day": day.isoformat(),
        "format": FORMAT,
        "pairs": {key: sorted([feed, scope] for feed, scope in pairs[key]) for key in sorted(pairs)},
        "seal": seal_of(salt, path_of(day, number)),
    }
    return json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def parse(data: bytes) -> Pairs:
    """The pairs of a provenance file, or ValueError for anything that is not exactly one (never a partial read)."""
    document = json.loads(data)
    if not isinstance(document, dict) or set(document) != KEYS or document["format"] != FORMAT:
        raise ValueError("not a provenance file")
    pairs = document["pairs"]
    if not isinstance(pairs, dict) or not isinstance(document["seal"], str):
        raise ValueError("not a provenance file")
    return {key: frozenset(_pair(item) for item in items) for key, items in pairs.items()}


def _pair(item: object) -> Pair:
    if not (isinstance(item, list) and len(item) == 2 and all(isinstance(part, str) for part in item)):
        raise ValueError("not a provenance file")
    return item[0], item[1]
