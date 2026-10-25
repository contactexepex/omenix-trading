"""G13's day records as G13c reads them: G13's own record-file reader over the verified Drive cache, only records of
G13's current method (an older method's back-fill stays in Drive but is never mixed in), each (underlying, day,
source) once."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from pathlib import Path

from ..price_distribution.record_files import read_records
from .constants import SOURCE_OF_LABEL


def current_records(records: Iterable[dict], method_sha256: str) -> Iterator[dict]:
    seen = set()
    for record in records:
        if record.get("method_sha256") != method_sha256 or record.get("label") not in SOURCE_OF_LABEL:
            continue
        key = (record["underlying"], record["day"], SOURCE_OF_LABEL[record["label"]])
        if key not in seen:
            seen.add(key)
            yield record


def cached_records(data_root: Path, method_sha256: str) -> Iterator[dict]:
    """`data_root`: the Drive cache's local `data` folder, synced by the caller."""
    return current_records(read_records(data_root), method_sha256)
