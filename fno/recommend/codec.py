"""Reading and writing a recommendation (story REC1a): the school's canonical JSON (equal records, equal bytes), read
strictly: only the exact canonical bytes read. A missing field (the candidate set and `evidence_cutoff` above all,
judge 620.1), an unknown field at any depth, an unknown code or a broken rule refuses the bytes; nothing is filled
in."""

from __future__ import annotations

import json
from dataclasses import fields

from .contracts import Recommendation, RecordRefused

FIELDS = frozenset(f.name for f in fields(Recommendation))
MISSING = "recommendation record lacks {names}"
UNKNOWN = "recommendation record has unknown fields {names}"
UNREADABLE = "recommendation record does not read: {kind}"
NOT_CANONICAL = "recommendation record is not in canonical form (a nested field added or a value respelled)"


def encode(record: Recommendation) -> bytes:
    return record.to_bytes()


def decode(data: bytes) -> Recommendation:
    try:
        plain = json.loads(data)
    except (UnicodeDecodeError, ValueError) as bad:
        raise RecordRefused(UNREADABLE.format(kind=type(bad).__name__)) from None
    if not isinstance(plain, dict):
        raise RecordRefused(UNREADABLE.format(kind=type(plain).__name__))
    _same_fields(set(plain))
    try:
        record = Recommendation.from_bytes(data)
    except RecordRefused:
        raise
    except (TypeError, ValueError, KeyError) as bad:
        raise RecordRefused(UNREADABLE.format(kind=type(bad).__name__)) from None
    if encode(record) != data:  # every record is written canonical, so any other spelling is not one of ours
        raise RecordRefused(NOT_CANONICAL)
    return record


def _same_fields(names: set[str]) -> None:
    if missing := FIELDS - names:
        raise RecordRefused(MISSING.format(names=", ".join(sorted(missing))))
    if unknown := names - FIELDS:
        raise RecordRefused(UNKNOWN.format(names=", ".join(sorted(unknown))))
