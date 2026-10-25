"""The example reasoning routine (story O6), proving the trigger path end to end: it takes the pointer a download job
fired, skips it when this version was already processed, reads the file from Drive, checks that the bytes are the
version named, and writes a small derived summary plus its "processed" record. Real routines replace the summary
with their reasoning and keep the same steps."""

from __future__ import annotations

import hashlib
import json

from ..storage.raw_store import RawFileStore
from .pointer import BatchPointer
from .records import PROCESSED, PipelineRecords

ALREADY_PROCESSED = "already processed: {key}"
MISSING = "not in Drive: {path}"
WRONG_VERSION = "the bytes in Drive are not version {version} (SHA-256 {found}); nothing written"
DONE = "processed: {lines} lines, {size} bytes; summary {derived}"


class DryRunRoutine:
    def __init__(self, project: RawFileStore, derived: RawFileStore, records: PipelineRecords, routine: str):
        self.project, self.derived, self.records, self.routine = project, derived, records, routine

    def process(self, pointer: BatchPointer) -> tuple[bool, str]:
        """(ok, the one line to print). Only a file that is missing or not the version named is not ok."""
        if self.records.has(PROCESSED, self.routine, pointer):
            return True, ALREADY_PROCESSED.format(key=pointer.key)
        data = self.project.get(pointer.path)
        if data is None:
            return False, MISSING.format(path=pointer.path)
        found = hashlib.sha256(data).hexdigest()
        if found != pointer.version:
            return False, WRONG_VERSION.format(version=pointer.version[:12], found=found[:12])
        derived = f"{self.routine}/{pointer.key}"
        self.derived.put(derived, _summary(pointer, data))
        self.records.mark(PROCESSED, self.routine, pointer, derived=derived)
        return True, DONE.format(lines=data.count(b"\n"), size=len(data), derived=derived)


def _summary(pointer: BatchPointer, data: bytes) -> bytes:
    first_line = data.split(b"\n", 1)[0][:200].decode("utf-8", errors="replace")
    body = {
        "pointer": pointer.to_text(),
        "size_bytes": len(data),
        "lines": data.count(b"\n"),
        "first_line": first_line,
    }
    return json.dumps(body, sort_keys=True).encode()
