"""The filings librarian (story A12): for each company, reads its filing lists, then fetches and archives every listed
XBRL file the manifest does not have yet. A stopped run is resumed by running it again: the lists are read again and
only files without a manifest row are fetched.

It stops by itself at its deadline (a scheduled run has a time limit), and at once when the exchange refuses us
(cooling off): the rest waits for the next run. What cannot be archived is recorded as a gap with its reason, a file
NSE itself serves cut off included (the same bytes on two downloads); failures (a list or file the exchange did not
answer, a file that is not XBRL) leave the run incomplete. Knows only the
interfaces, never a concrete store, index or source.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime

import requests

from ..http_pacing import SourceCoolingOff
from ..storage.raw_source import NseArchiveSource, RawFileRefused, RawSourceUnavailable
from ..storage.raw_store import RawFileConflict, StoredCopyDamaged
from .archive import FilingArchive
from .filing import Filing, FilingGap
from .index import FilingIndex
from .xbrl import TruncatedXbrl

NO_FILINGS = "NSE lists no {kind} filing made public since {since}"
NO_FILE = "NSE lists {count} filing(s) with no XBRL file (periods {first} to {last})"
NOT_SERVED = "NSE's link for the {period} filing answers 'not found': {url}"
TRUNCATED = (
    "NSE serves a truncated or malformed file for the {period} filing, the same twice ({size} bytes, SHA-256 {sha256}):"
    " {error}"
)
UNEXPECTED_LINK = "NSE's link for the {period} filing is outside its XBRL folder: {url}"
STORE_STOPPED = "the archive store stopped answering at {symbol}: {error}; rows so far are kept, the next run resumes"
LIST_ERRORS = (requests.RequestException, RuntimeError, ValueError, KeyError, TypeError)


@dataclass
class FilingsReport:
    companies: int = 0
    checked: list[str] = field(default_factory=list)
    saved: int = 0
    bytes_saved: int = 0
    present: int = 0
    gaps: list[FilingGap] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    failed: set[str] = field(default_factory=set)  # companies with a failure: not finished, the next run retries
    stopped: str = ""  # why the run stopped before checking every company ("" when it did not)

    @property
    def finished(self) -> list[str]:
        """Companies checked without a failure: their step needs nothing more from them."""
        return [s for s in self.checked if s not in self.failed]

    @property
    def complete(self) -> bool:
        return not self.stopped and not self.failures and len(self.checked) == self.companies


class FilingsLibrarian:
    def __init__(
        self,
        indexes: Sequence[FilingIndex],
        source: NseArchiveSource,
        archive: FilingArchive,
        clock: Callable[[], datetime],
        log: Callable[[str], None] = print,
    ):
        self.indexes, self.source, self.archive, self.clock, self.log = indexes, source, archive, clock, log

    def run(self, companies: Sequence[str], since: date, deadline: datetime) -> FilingsReport:
        report = FilingsReport(companies=len(companies))
        for done, symbol in enumerate(companies, start=1):
            if self.clock() >= deadline:
                report.stopped = f"deadline reached after {len(report.checked)} companies; the next run resumes"
                break
            try:
                self._company(symbol, since, deadline, report)
            except (SourceCoolingOff, RawSourceUnavailable) as exc:
                report.stopped = f"NSE stopped answering at {symbol}: {exc}"
                break
            except requests.RequestException as exc:  # the store (Drive) failed after its own retries
                report.stopped = STORE_STOPPED.format(symbol=symbol, error=exc)
                break
            self.log(f"{done}/{len(companies)} {symbol}: saved {report.saved}, already there {report.present}")
        return report

    def _company(self, symbol: str, since: date, deadline: datetime, report: FilingsReport) -> None:
        without_file: dict[str, list[date]] = {}
        for index in self.indexes:
            try:
                filings = index.filings(symbol, since)
            except SourceCoolingOff:
                raise
            except LIST_ERRORS as exc:
                report.failures.append(f"{symbol}: {index.name} not read: {exc}")
                report.failed.add(symbol)
                continue
            for filing in filings:
                if self.clock() >= deadline:
                    return  # not marked as checked: the next run reads this company again
                if filing.url:
                    self._filing(filing, report)
                else:
                    without_file.setdefault(filing.kind, []).append(filing.period_end)
        for kind, periods in sorted(without_file.items()):
            reason = NO_FILE.format(count=len(periods), first=min(periods), last=max(periods))
            report.gaps.append(FilingGap(symbol, kind, reason))
        for kind in sorted({i.kind for i in self.indexes}):
            if not self.archive.has_any(symbol, kind, since):
                report.gaps.append(FilingGap(symbol, kind, NO_FILINGS.format(kind=kind, since=since)))
        report.checked.append(symbol)

    def _filing(self, filing: Filing, report: FilingsReport) -> None:
        period = f"{filing.period_end} {filing.consolidation}".strip()
        gap = self._gap(filing, period)
        if gap:
            report.gaps.append(FilingGap(filing.symbol, filing.kind, gap))
            return
        if self.archive.has(filing):
            report.present += 1
            return
        try:
            data = self.source.fetch(filing.path)
        except RawFileRefused as exc:  # this file only; NSE unavailable stops the run in `run` (A9b)
            self._fail(filing, f"NSE refused it: {exc}", report)
            return
        if data is None:
            report.gaps.append(FilingGap(filing.symbol, filing.kind, NOT_SERVED.format(period=period, url=filing.url)))
            return
        try:
            self.archive.save(filing, data)
        except TruncatedXbrl as exc:
            self._truncated(filing, period, data, exc, report)
            return
        except (ValueError, RawFileConflict, StoredCopyDamaged) as exc:  # not XBRL, another file there, bad copy
            self._fail(filing, f"not saved: {exc}", report)
            return
        report.saved += 1
        report.bytes_saved += len(data)

    def _truncated(self, filing: Filing, period: str, data: bytes, error: Exception, report: FilingsReport) -> None:
        """NSE's own copy is cut off when a second download gives the same bytes: a gap with its size and SHA-256 (a
        later fixed copy is fetched and saved by the next run, since no row exists). A differing or failed second
        download is a failure, retried next run. The file is never saved either way."""
        try:
            again = self.source.fetch(filing.path)
        except RawFileRefused as exc:
            self._fail(filing, f"not saved: {error}; the second download failed: {exc}", report)
            return
        if again != data:
            self._fail(filing, f"not saved: {error}; a second download differed", report)
            return
        reason = TRUNCATED.format(period=period, size=len(data), sha256=hashlib.sha256(data).hexdigest(), error=error)
        report.gaps.append(FilingGap(filing.symbol, filing.kind, reason))

    @staticmethod
    def _fail(filing: Filing, why: str, report: FilingsReport) -> None:
        report.failures.append(f"{filing.symbol} {filing.filename}: {why}")
        report.failed.add(filing.symbol)

    def _gap(self, filing: Filing, period: str) -> str:
        if self.source.url_for(filing.path) != filing.url:
            return UNEXPECTED_LINK.format(period=period, url=filing.url)
        return ""
