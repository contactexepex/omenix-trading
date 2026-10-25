"""A source that offers every file it reads in full to the revision archive (story A11), so any pass over a
dataset (A8's write-time sweep, `data-revisions sweep`) stores what it finds instead of only reporting it.

Its `last_written` reads the whole file, not headers only: a rewrite is proven by the bytes' SHA-256, and the bytes
are needed to keep the version. At NSE's one-request-per-second pacing a full read takes no longer than a header read
for these files (a few KB to a few hundred KB).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime

from .raw_source import (
    COOLING_OFF_STOP,
    NOT_PUBLISHED_REASON,
    PublishedFile,
    RawFileSource,
    RawSourceCoolingOff,
    RawSourceUnavailable,
)
from .revisions import RevisionArchive


class RevisionCapturingSource(RawFileSource):
    def __init__(self, source: RawFileSource, archive: RevisionArchive):
        self.source, self.archive = source, archive
        self.name, self.dataset = source.name, source.dataset
        self.first_day, self.last_day = source.first_day, source.last_day

    def fetch(self, path: str) -> bytes | None:
        found = self.fetch_published(path)
        return None if found is None else found.data

    def fetch_published(self, path: str) -> PublishedFile | None:
        found = self.source.fetch_published(path)
        if found is not None:
            self.archive.capture(path, found)
        return found

    def last_written(self, path: str) -> datetime | None:
        found = self.fetch_published(path)
        return found.last_modified if found else None


@dataclass
class RevisionSweepResult:
    checked: int = 0
    unanswered: dict[str, str] = field(default_factory=dict)  # path -> why: unreachable, refused or no longer served
    stopped: str = ""  # the host paused after refusals: the pass stopped, the rest not read (A9b)


def sweep_revisions(source: RevisionCapturingSource, paths: Iterable[str]) -> RevisionSweepResult:
    """Reads every path once from the source; new versions land in the source's archive (`archive.stored`)."""
    result, paths = RevisionSweepResult(), list(paths)
    for done, path in enumerate(paths):
        try:
            found = source.fetch_published(path)
        except RawSourceCoolingOff as paused:  # every later file would fail the same way
            result.stopped = COOLING_OFF_STOP.format(error=paused, left=len(paths) - done)
            break
        except RawSourceUnavailable as failed:
            found, why = None, str(failed)
        else:
            why = NOT_PUBLISHED_REASON
        result.checked += 1
        if found is None:
            result.unanswered[path] = why
    return result
