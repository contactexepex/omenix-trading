"""The gate's revision sink on the existing A11 archive (`storage/revisions.py`): a later version of a recorded file is
saved to the revisions area with its index row, deduplicated against the record and every version already indexed."""

from __future__ import annotations

from datetime import datetime

from fno.ingestion.promotion.gate import RevisionSink
from fno.ingestion.storage.raw_source import PublishedFile
from fno.ingestion.storage.revisions import RevisionArchive


class ArchiveRevisionSink(RevisionSink):
    def __init__(self, archive: RevisionArchive):
        self.archive = archive

    def capture(self, path: str, data: bytes, found_at: datetime) -> bool:
        """`found_at` is when the version was staged (the time we fetched it), not when the gate ran."""
        return self.archive.capture(path, PublishedFile(data, None), found_at) is not None
