"""Which raw NSE files the archive is missing, holds damaged or holds without a fingerprint, against NSE's session
calendar (stories A1, A10), and how many days have later NSE versions in the revisions area (A11).

Read-only: it only calls `RawFileStore.get`. A session without a file fails unless a sourced exception explains it; a
file whose SHA-256 differs from its manifest row is damaged; a file with no manifest row is only content-checked, so
the result is not complete until it has one. A file on a day the calendar calls closed is reported for review.
"""

from __future__ import annotations

import csv
import hashlib
from collections.abc import Callable, Mapping
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

from ..research_data.calendar import SessionCalendar
from .raw_source import NseArchiveSource
from .raw_store import RawFileStore

EXCEPTION_FIELDS = ("dataset", "date", "reason", "source_url")
TABLE_HEADER = (
    f"{'dataset':<36} {'from':>10} {'to':>10} {'expected':>8} {'present':>7} {'missing':>7} {'damaged':>7} "
    f"{'no sha':>6} {'revised':>7}"
)

INCOMPLETE = "INCOMPLETE: missing, damaged or unfingerprinted files above"

Validator = Callable[[str, bytes], None]  # raises ValueError when the file is damaged or not in its schema


@dataclass(frozen=True)
class CoverageDataset:
    source: type[NseArchiveSource]
    validate: Validator
    fingerprints: Mapping[str, str] = field(default_factory=dict)  # file name -> SHA-256 (the dataset's manifest)
    revisions: Mapping[str, int] = field(default_factory=dict)  # file name -> later NSE versions archived (A11)

    def check(self, filename: str, data: bytes) -> bool:
        """Verifies a file (ValueError when its SHA-256 differs from its manifest row or its content is damaged);
        True when the manifest has it, False when only its content could be checked."""
        want = self.fingerprints.get(filename)
        if want is not None and hashlib.sha256(data).hexdigest() != want:
            raise ValueError(f"{filename}: SHA-256 differs from the manifest")
        self.validate(filename, data)
        return want is not None


@dataclass
class DatasetCoverage:
    dataset: str
    start: date
    end: date
    expected: int = 0
    present: int = 0
    missing: list[date] = field(default_factory=list)
    damaged: list[tuple[date, str]] = field(default_factory=list)
    excepted: list[tuple[date, str]] = field(default_factory=list)
    unexpected: list[date] = field(default_factory=list)
    unfingerprinted: list[date] = field(default_factory=list)  # present and content-checked, but no manifest row
    revised: list[tuple[date, int]] = field(default_factory=list)  # days with later NSE versions archived (A11)

    @property
    def ok(self) -> bool:
        return not (self.missing or self.damaged or self.unfingerprinted)


def read_exceptions(path: Path) -> dict[tuple[str, date], str]:
    """(dataset, day) -> reason, for sessions whose file is explained instead of archived: NSE never published one, or
    NSE's own file is refused by the content check (A23: fractional contracts); each row needs a source link."""
    if not path.is_file():
        return {}
    exceptions = {}
    for number, row in enumerate(csv.DictReader(path.read_text(encoding="utf-8").splitlines()), start=2):
        if tuple(row) != EXCEPTION_FIELDS or not (row["source_url"] or "").startswith("https://"):
            raise ValueError(f"{path.name} line {number}: needs {','.join(EXCEPTION_FIELDS)} with an https source")
        exceptions[(row["dataset"], date.fromisoformat(row["date"]))] = row["reason"]
    return exceptions


def archive_range(source: type[NseArchiveSource], start: date | None, end: date) -> tuple[date, date]:
    """The requested range clipped to the days the source's archive keeps files for (start None: its first day)."""
    start = start or source.first_day
    return max(start, source.first_day or start), min(end, source.last_day or end)


def days_between(start: date, end: date) -> list[date]:
    return [start + timedelta(offset) for offset in range((end - start).days + 1)]


DEFAULT_WORKERS = 8  # files read at the same time (Drive allows far more requests per minute than this makes)


class CoverageCheck:
    def __init__(
        self,
        store: RawFileStore,
        calendar: SessionCalendar,
        exceptions: dict[tuple[str, date], str],
        workers: int = DEFAULT_WORKERS,
    ):
        self.store, self.calendar, self.exceptions, self.workers = store, calendar, exceptions, workers

    def run(self, dataset: CoverageDataset, start: date | None, end: date) -> DatasetCoverage:
        source = dataset.source
        start, end = archive_range(source, start, end)
        result = DatasetCoverage(source.dataset, start, end)
        days = days_between(start, end)
        with ThreadPoolExecutor(max_workers=self.workers) as pool:  # reads in parallel, results in day order
            for day, data in zip(days, pool.map(lambda d: self.store.get(source.path_for(d)), days)):
                self._check_day(dataset, day, data, result)
        return result

    def _check_day(self, dataset: CoverageDataset, day: date, data: bytes | None, result: DatasetCoverage) -> None:
        source = dataset.source
        if not self.calendar.is_session(day):
            if data is not None:
                result.unexpected.append(day)
            return
        result.expected += 1
        if data is None:
            reason = self.exceptions.get((source.dataset, day))
            if reason:
                result.excepted.append((day, reason))
            else:
                result.missing.append(day)
            return
        try:
            fingerprinted = dataset.check(source.filename_for(day), data)
        except ValueError as exc:
            result.damaged.append((day, str(exc)))
            return
        result.present += 1
        revisions = dataset.revisions.get(source.filename_for(day), 0)
        if revisions:
            result.revised.append((day, revisions))
        if not fingerprinted:
            result.unfingerprinted.append(day)


def report_lines(results: list[DatasetCoverage]) -> list[str]:
    lines = [TABLE_HEADER]
    for r in results:
        lines.append(
            f"{r.dataset:<36} {r.start:%Y-%m-%d} {r.end:%Y-%m-%d} {r.expected:>8} {r.present:>7} "
            f"{len(r.missing):>7} {len(r.damaged):>7} {len(r.unfingerprinted):>6} {len(r.revised):>7}"
        )
    for r in results:
        lines += [f"missing  {r.dataset} {day}" for day in r.missing]
        lines += [f"damaged  {r.dataset} {day}: {reason}" for day, reason in r.damaged]
        lines += [f"excepted {r.dataset} {day}: {reason}" for day, reason in r.excepted]
        lines += [f"unexpected file (calendar says closed; review) {r.dataset} {day}" for day in r.unexpected]
        lines += [f"no fingerprint (content checked only) {r.dataset} {day}" for day in r.unfingerprinted]
        lines += [f"revised (later NSE versions in revisions/) {r.dataset} {day}: {n}" for day, n in r.revised]
    verdict = "complete" if all(r.ok for r in results) else INCOMPLETE
    return [*lines, f"result: {verdict}"]
