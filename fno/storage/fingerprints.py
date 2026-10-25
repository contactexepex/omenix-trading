"""SHA-256 fingerprints of a dataset's archived files, read from a store (read-only) for its manifest (stories A9,
A10), and a spot-check of a sample against the source's live bytes: a difference is reported as a rewrite, never
"fixed" in the archive (raw files never change).
"""

from __future__ import annotations

import hashlib
from concurrent.futures import ThreadPoolExecutor
from datetime import date

from ..research_data.calendar import SessionCalendar
from .coverage import DEFAULT_WORKERS, archive_range, days_between
from .manifest_folder import Fingerprint
from .raw_source import COOLING_OFF_STOP, NseArchiveSource, RawSourceCoolingOff, RawSourceUnavailable
from .raw_store import RawFileStore


def fingerprint_store(
    store: RawFileStore,
    source: type[NseArchiveSource],
    calendar: SessionCalendar,
    start: date | None,
    end: date,
    workers: int = DEFAULT_WORKERS,
) -> list[Fingerprint]:
    """The fingerprint of every file the store holds for the source's sessions from start to end, in day order."""
    days = [day for day in days_between(*archive_range(source, start, end)) if calendar.is_session(day)]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        files = list(pool.map(lambda day: store.get(source.path_for(day)), days))
    return [Fingerprint.of(source, source.path_for(day), data) for day, data in zip(days, files) if data is not None]


NO_ANSWER = "NO ANSWER"  # the source failed after its retries (A9b)


def compare_with_source(source: NseArchiveSource, fingerprints: list[Fingerprint]) -> list[str]:
    """One line per file: whether the source's live bytes still equal the archived fingerprint."""
    lines = []
    for done, f in enumerate(fingerprints):
        try:
            live = source.fetch(source.path_for(f.day))
        except RawSourceCoolingOff as paused:  # every later file would fail the same way
            lines.append(f"{NO_ANSWER}: {COOLING_OFF_STOP.format(error=paused, left=len(fingerprints) - done)}")
            break
        except RawSourceUnavailable as failed:  # named per file; the other files are still compared
            lines.append(f"{f.day} {f.url}: {NO_ANSWER}: {failed}")
            continue
        if live is None:
            lines.append(f"{f.day} {f.url}: the source no longer serves it (archive copy kept)")
        elif hashlib.sha256(live).hexdigest() == f.sha256:
            lines.append(f"{f.day} {f.url}: identical")
        else:
            lines.append(f"{f.day} {f.url}: NSE REWRITE: live bytes differ from the archived file (archive kept)")
    return lines
