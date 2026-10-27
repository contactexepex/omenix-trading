"""The formats of the article file and how two files are compared (NP2a). One definition, used by the reader of the
Record, the planner and the staging cleanup, so no two of them can disagree about what an article file is.

A file is OURS only when its `format` is exactly an integer we know and its keys are exactly that format's keys: a
file missing a key, carrying an unknown one, or saying `true` or `1.0` is damaged, never "almost the same article".
Two files are the same version when every field they both define, except the uncompared ones, is equal: all of a
format's own fields when both are of one format, the older format's fields when they differ (a format 1 file holds
no source facts)."""

from __future__ import annotations

import json
from typing import Any

V1_FIELDS = frozenset({
    "key", "kind", "source", "title", "summary", "canonical_url", "published_at", "time_source", "first_seen_at",
})  # fmt: skip
V2_FIELDS = V1_FIELDS | {"source_domain", "wrapper_link"}
FIELDS_OF = {1: V1_FIELDS, 2: V2_FIELDS}
READABLE_FORMATS = tuple(FIELDS_OF)
# when it was first seen, and a redirect token that may change between polls of one item
UNCOMPARED = frozenset({"first_seen_at", "wrapper_link"})


def read_document(data: bytes) -> tuple[int, dict[str, Any]] | None:
    """(format, fields) of an article file of ours, else None."""
    try:
        document = json.loads(data)
    except (ValueError, UnicodeDecodeError):
        return None
    if not isinstance(document, dict):
        return None
    format_number = document.get("format")
    if type(format_number) is not int or format_number not in FIELDS_OF:
        return None
    fields = {k: v for k, v in document.items() if k != "format"}
    return (format_number, fields) if set(fields) == FIELDS_OF[format_number] else None


def same_version(held: bytes, new: bytes) -> bool:
    first, second = read_document(held), read_document(new)
    if first is None or second is None:
        return False  # a damaged file differs from every article
    compared = FIELDS_OF[min(first[0], second[0])] - UNCOMPARED
    return all(first[1][k] == second[1][k] for k in compared)


def fixed_bytes(data: bytes) -> bytes | None:
    """The compared fields of a file as canonical bytes (what a revision's name is made of); None for a damaged file."""
    document = read_document(data)
    if document is None:
        return None
    fields = {k: v for k, v in document[1].items() if k not in UNCOMPARED}
    return json.dumps(fields, sort_keys=True).encode()
