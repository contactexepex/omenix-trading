"""G13's day records read back from the verified Drive cache for scoring (section 6): live day files and back-fill
files (their `records`); score reports are skipped."""

from __future__ import annotations

import gzip
import json
from collections.abc import Iterator
from pathlib import Path

from .backfill import SCHEMA as BACKFILL_SCHEMA
from .folders import BACKFILL, LIVE


def read_records(cache_root: Path) -> Iterator[dict]:
    for folder in (LIVE, BACKFILL):
        for path in sorted((cache_root / folder).rglob("*.json*")):
            data = path.read_bytes()
            document = json.loads(gzip.decompress(data) if path.suffix == ".gz" else data)
            if document.get("schema") == BACKFILL_SCHEMA:
                yield from document["records"]
            else:
                yield document
