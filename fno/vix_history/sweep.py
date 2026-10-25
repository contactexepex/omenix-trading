"""Looks for later NSE versions of the archived India VIX months (story A15 with A11's revision rule).

Each archived month is read again from NSE. An answer that fails the month check (an HTML error page served with
HTTP 200, a cut answer) is listed and never kept, so only a real month file can become a revision. A valid answer
with other bytes is saved by A11's revision archive beside the original, never over it, and its changes are named
day by day. The derived table is never changed by a revision.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import date

from ..storage.raw_source import (
    COOLING_OFF_STOP,
    NOT_PUBLISHED_REASON,
    RawFileSource,
    RawSourceCoolingOff,
    RawSourceUnavailable,
)
from ..storage.raw_store import RawFileStore
from ..storage.revisions import RevisionArchive
from .month_file import VixDay, VixMonthReader


@dataclass
class SweepReport:
    checked: int = 0
    unanswered: dict[date, str] = field(default_factory=dict)  # month -> why: unreachable, refused or not served
    invalid: list[tuple[date, str]] = field(default_factory=list)
    revised: list[tuple[date, list[str]]] = field(default_factory=list)  # month, its changes day by day
    not_archived: list[date] = field(default_factory=list)  # NSE answered other bytes but the original is missing
    stopped: str = ""  # NSE's host paused after refusals: the sweep stopped, the rest not read (A9b)

    def lines(self) -> list[str]:
        lines = [f"India VIX revisions: {self.checked} months read, {len(self.revised)} with a new NSE version"]
        lines += [f"no answer {m:%Y-%m}: {why}" for m, why in self.unanswered.items()]
        lines += [f"answer failed the check, not kept {m:%Y-%m}: {why}" for m, why in self.invalid]
        lines += [f"revised {m:%Y-%m}: {change}" for m, changes in self.revised for change in changes]
        lines += [f"original MISSING from the archive, nothing compared {m:%Y-%m}" for m in self.not_archived]
        return lines + ([f"STOPPED: {self.stopped}"] if self.stopped else [])


class VixRevisionSweep:
    def __init__(
        self,
        source: RawFileSource,
        archive: RevisionArchive,
        raw: RawFileStore,
        path_for: Callable[[date], str],
        reader: VixMonthReader,
        fingerprints: Mapping[date, str],
    ):
        """`fingerprints`: month -> SHA-256 of the archived original (its manifest row): an answer with the same
        SHA-256 is no revision, decided without reading Drive."""
        self.source, self.archive, self.raw, self.path_for, self.reader = source, archive, raw, path_for, reader
        self.fingerprints = fingerprints

    def sweep(self, months: list[date]) -> SweepReport:
        report = SweepReport()
        for done, month in enumerate(months):
            try:
                self._check(month, report)
            except RawSourceCoolingOff as paused:  # every later month would fail the same way
                report.stopped = COOLING_OFF_STOP.format(error=paused, left=len(months) - done)
                break
            report.checked += 1
        return report

    def _check(self, month: date, report: SweepReport) -> None:
        path = self.path_for(month)
        try:
            found = self.source.fetch_published(path)
        except RawSourceCoolingOff:
            raise
        except RawSourceUnavailable as failed:  # retried already where worth it (A9b); a refusal included
            report.unanswered[month] = str(failed)
            return
        if found is None:
            report.unanswered[month] = NOT_PUBLISHED_REASON
            return
        if hashlib.sha256(found.data).hexdigest() == self.fingerprints.get(month):
            return  # the archived original itself
        try:
            revised = self.reader.read(found.data, month)
        except ValueError as exc:
            report.invalid.append((month, str(exc)))
            return
        if self.archive.capture(path, found) is not None:
            report.revised.append((month, self._changes(path, month, revised)))
        elif path in self.archive.not_archived:
            report.not_archived.append(month)

    def _changes(self, path: str, month: date, revised: list[VixDay]) -> list[str]:
        """The revision's changes against the archived original (named when the original cannot be read)."""
        data = self.raw.get(path)
        if data is None:
            return ["kept, but the original is MISSING from the archive: nothing compared"]
        try:
            return day_changes(self.reader.read(data, month), revised)
        except ValueError as exc:
            return [f"kept, but the original fails the check ({exc}): nothing compared"]


def day_changes(original: list[VixDay], revised: list[VixDay]) -> list[str]:
    """What a revision changed, one line per day: a day added, removed, or with other values."""
    before, after = {d.day: d for d in original}, {d.day: d for d in revised}
    changes = []
    for day in sorted(set(before) | set(after)):
        old, new = before.get(day), after.get(day)
        if old != new:
            changes.append(f"{day}: {_levels(old)} -> {_levels(new)}")
    return changes or ["same days and values, other bytes"]


def _levels(day: VixDay | None) -> str:
    return "absent" if day is None else f"O {day.open} H {day.high} L {day.low} C {day.close}"
