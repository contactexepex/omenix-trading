"""The source contract of the daily packs (story E2, design 13.5): every item a pack holds names its source and the
time it became available; an item available after the pack's cutoff, or with no availability time, is refused and
listed by name, never silently used. Packs are canonical JSON (sorted keys, no build time), so the same inputs give
byte-identical files and the same SHA-256."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

from ..models import IST


class PackError(ValueError):
    """A pack that may not be built or written: the message names the input or file."""


@dataclass(frozen=True)
class PackItem:
    name: str
    value: object  # JSON-ready
    source: str
    available_at: str  # ISO time with its offset; "" when the source gives none

    def record(self) -> dict:
        return {"name": self.name, "value": self.value, "source": self.source, "available_at": self.available_at}


def available_time(text: str) -> datetime | None:
    """The item's availability as an IST-aware time; None when missing or unreadable."""
    try:
        moment = datetime.fromisoformat(text)
    except (TypeError, ValueError):
        return None
    return (moment if moment.tzinfo else moment.replace(tzinfo=IST)).astimezone(IST)


def admit(items: Iterable[PackItem], cutoff: datetime) -> tuple[tuple[PackItem, ...], tuple[dict, ...]]:
    """(items available at or before the cutoff, refusals with each item's name and reason), both in name order."""
    admitted, refused = [], []
    for item in items:
        moment = available_time(item.available_at)
        if moment is None:
            refused.append({"name": item.name, "available_at": item.available_at, "reason": "no availability time"})
        elif moment > cutoff:
            refused.append({"name": item.name, "available_at": item.available_at, "reason": "after the cutoff"})
        else:
            admitted.append(item)
    names = [item.name for item in admitted]
    if len(names) != len(set(names)):
        raise PackError(f"two items share a name: {sorted({n for n in names if names.count(n) > 1})}")
    return tuple(sorted(admitted, key=lambda i: i.name)), tuple(sorted(refused, key=lambda r: r["name"]))


def canonical_json(body: dict) -> bytes:
    return (json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
