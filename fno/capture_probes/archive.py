"""A source's slot, saved once in Drive (story MS-P0b section 5, O9): one gz JSON Lines file per source and slot, its
receipt in `receipts/`. The same bytes again are a no-op; different bytes under the same name stop that slot's save
with a named line, never overwrite."""

from __future__ import annotations

import gzip
import json

from ..storage.raw_store import RawFileConflict

SAVED, FAILED, CONFLICT, NOTHING = "ok", "failed", "conflict", "none"


def slot_path(source: str, session: str, slot: str) -> str:
    return f"{source}/{session}/{slot.replace(':', '')}.jsonl.gz"


def slot_bytes(lines: list[dict]) -> bytes:
    text = "".join(json.dumps(line, sort_keys=True, default=str) + "\n" for line in lines)
    return gzip.compress(text.encode(), mtime=0)  # no time in the header: one slot's lines give one file


class SlotArchive:
    def __init__(self, store, area: str):
        """`store`: O9's `DataStore` (or a dry run's folder store), with `put(path, data)`."""
        self.store, self.area = store, area

    def save(self, source: str, session: str, slot: str, lines: list[dict]) -> str:
        if not lines:
            return NOTHING
        try:
            self.store.put(f"{self.area}/{slot_path(source, session, slot)}", slot_bytes(lines))
        except RawFileConflict:
            return CONFLICT
        except Exception:  # any Drive failure (network, sign-in, quota) is a failed write, counted, never raised
            return FAILED
        return SAVED
