"""The historical-data librarian: fills one dataset's gaps in a store from the dataset's source (story A9).

For every session in the range it reads the store first: a file already there is verified and kept as it is (never
replaced, even when damaged: that is reported). A missing file is fetched from the source, verified (its schema, and
its SHA-256 where a manifest has it) and only then saved. A stopped run is resumed by running it again: only what is
still missing is fetched, and a file already there without a manifest row (a run stopped before its commit) gets its
row. Knows only the interfaces, never a concrete store or source.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date

from ..research_data.calendar import SessionCalendar
from .coverage import CoverageDataset, archive_range, days_between
from .raw_source import NseArchiveSource
from .raw_store import RawFileStore, StoredCopyDamaged

PROGRESS_EVERY = 100  # sessions between progress lines
PROGRESS_LINE = "{dataset}: {done}/{total} sessions; uploaded {uploaded}, already there {present}"


@dataclass
class FillReport:
    dataset: str
    start: date
    end: date
    sessions: int = 0
    present: int = 0  # already in the store and verified
    uploaded: list[date] = field(default_factory=list)
    damaged: list[tuple[date, str]] = field(default_factory=list)  # in the store but failing verification; left alone
    rejected: list[tuple[date, str]] = field(default_factory=list)  # the source's file failed verification; not saved
    not_published: list[date] = field(default_factory=list)  # a session the source has no file for, unexplained
    excepted: int = 0  # sessions with a sourced reason why no file exists

    @property
    def complete(self) -> bool:
        return not (self.damaged or self.rejected or self.not_published)


class RawDataLibrarian:
    def __init__(
        self,
        store: RawFileStore,
        source: NseArchiveSource,
        dataset: CoverageDataset,
        calendar: SessionCalendar,
        exceptions: dict[tuple[str, date], str],
        log: Callable[[str], None] = print,
    ):
        """`dataset` verifies each file (content, and SHA-256 where its manifest has a row); `store` should record a
        manifest row for each file it saves (FingerprintingStore)."""
        self.store, self.source, self.dataset = store, source, dataset
        self.calendar, self.exceptions, self.log = calendar, exceptions, log

    def fill(self, start: date | None, end: date) -> FillReport:
        start, end = archive_range(type(self.source), start, end)
        report = FillReport(self.source.dataset, start, end)
        sessions = [day for day in days_between(start, end) if self.calendar.is_session(day)]
        report.sessions = len(sessions)
        for done, day in enumerate(sessions, start=1):
            self._fill_day(day, report)
            if done % PROGRESS_EVERY == 0 or done == len(sessions):
                self.log(self._progress(report, done))
        return report

    def _fill_day(self, day: date, report: FillReport) -> None:
        path, filename = self.source.path_for(day), self.source.filename_for(day)
        stored = self.store.get(path)
        if stored is not None:
            problem = self._problem(filename, stored)
            if problem:
                report.damaged.append((day, problem))
                return
            if filename not in self.dataset.fingerprints:  # saved by a run stopped before its manifest commit
                self.store.put(path, stored)  # the same bytes: the store keeps its copy and the row is written
            report.present += 1
            return
        if (self.source.dataset, day) in self.exceptions:
            report.excepted += 1
            return
        data = self.source.fetch(path)
        if data is None:
            report.not_published.append(day)
            return
        problem = self._problem(filename, data)
        if problem:
            report.rejected.append((day, problem))
            return
        try:
            self.store.put(path, data)
        except StoredCopyDamaged as exc:
            report.damaged.append((day, str(exc)))
            return
        report.uploaded.append(day)

    def _problem(self, filename: str, data: bytes) -> str | None:
        try:
            self.dataset.check(filename, data)
        except ValueError as exc:
            return str(exc)
        return None

    @staticmethod
    def _progress(report: FillReport, done: int) -> str:
        return PROGRESS_LINE.format(
            dataset=report.dataset,
            done=done,
            total=report.sessions,
            uploaded=len(report.uploaded),
            present=report.present,
        )


def fill_report_lines(report: FillReport) -> list[str]:
    lines = [
        f"{report.dataset} {report.start} to {report.end}: {report.sessions} sessions, {report.present} already there "
        f"and verified, {len(report.uploaded)} uploaded, {report.excepted} with a sourced exception"
    ]
    lines += [f"damaged in store (left as is) {day}: {reason}" for day, reason in report.damaged]
    lines += [f"rejected from source (not saved) {day}: {reason}" for day, reason in report.rejected]
    lines += [f"not published by the source {day}" for day in report.not_published]
    verdict = "complete" if report.complete else "INCOMPLETE: see the lines above"
    return [*lines, f"result: {verdict}"]
