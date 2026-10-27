"""One page-read pass (NP4b; NP0 section 2d, 2e), over the Record. Newest first over the last `LOOKBACK_DAYS` days it
finds the articles worth a page read, fetches each page through the guarded `PageFetcher` (NP4a), measures it
(`extract.py`) and, with `apply`, writes a write-once read file. Two kinds of article:

- a Google News article (in the wrapper index, NP2d) that has a resolution file (NP2c): the page is the resolved URL;
- any other article of the look-back (not in the wrapper index): the page is its own canonical link.

Bounded by construction: at most `PAGES` pages fetched, at most `MAX_RECORD_READS` Record files read to choose them,
and at most `BUDGET_SECONDS` of total run time (the clock is checked before every page; the rest are counted as
`budget_stopped` and alerted), so a slow or silent outlet can never run the job past its limit. A page that gives no
facts, or is refused, writes nothing and is tried again on the next pass. Without `apply` it still fetches (the
probe)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import date, datetime, timedelta
from urllib.parse import urlsplit

from fno.ingestion.news import codes
from fno.ingestion.news.article.article_file import article_from_bytes
from fno.ingestion.news.pages import model
from fno.ingestion.news.pages.model import PageFetcher
from fno.ingestion.news.reads.extract import extract
from fno.ingestion.news.reads.limits import BUDGET_SECONDS, LOOKBACK_DAYS, MAX_RECORD_READS, PAGES
from fno.ingestion.news.reads.links import fetchable
from fno.ingestion.news.reads.pass_note import PassNotes
from fno.ingestion.news.reads.plan import ReadPlanner
from fno.ingestion.news.reads.queue import MaterialQueue
from fno.ingestion.news.reads.read_file import build_read, read_path
from fno.ingestion.news.reads.report import ReadReport
from fno.ingestion.news.record.manifest import NewsManifest
from fno.ingestion.news.record.planner import article_path
from fno.ingestion.news.resolve.resolution_file import parse_resolution, resolution_path
from fno.ingestion.news.sources.rules import SourceRules, plain_host
from fno.ingestion.news.write_once import WriteOnceWriter, Written
from fno.ingestion.storage.raw_store import RawFileConflict, RawFileStore
from fno.ingestion.storage.row_log import TableFileBroken
from fno.shared.models import now_utc

FAILING_MIN_ASKED, FAILING_BELOW_SHARE, NOTHING_OK_MIN_ASKED = 10, 0.5, 3
NOT_A_FAULT = (model.ROBOTS_DISALLOWED, model.HOST_STOPPED, model.HOST_NOT_ALLOWED)  # expected, not a failing reader


class ReadPass:
    def __init__(self, record: RawFileStore, articles: NewsManifest, wrappers: NewsManifest, resolved: NewsManifest,
                 fetcher: PageFetcher, rules: SourceRules, writer: WriteOnceWriter,
                 clock: Callable[[], float], planner: ReadPlanner | None = None, notes: PassNotes | None = None,
                 now: Callable[[], datetime] = now_utc):  # fmt: skip
        """`record`: the Record, read only. `articles`, `wrappers`, `resolved`: the three manifests of the checkout.
        `writer`: the only way to write, with the reads manifest. `clock`: monotonic seconds, for the run budget.
        `planner`, `notes` (NP8): the order of reads (material first when the owner's two private files are usable) and
        the write-once pass note; without them the pass reads newest first, as it always did."""
        self.record, self.articles, self.wrappers, self.resolved = record, articles, wrappers, resolved
        self.fetcher, self.rules, self.writer, self.clock = fetcher, rules, writer, clock
        self.planner, self.notes, self.now = planner, notes, now

    def run(self, today: date, apply: bool, pages: int = PAGES, budget: float = BUDGET_SECONDS) -> ReadReport:
        report = ReadReport(apply)
        started = self.clock()
        if not self._ready(report, apply):
            return report
        moment = self.now()
        plan = self.planner.plan(report) if self.planner else None
        queue = None
        if plan and plan.note:
            queue = MaterialQueue(self.record, self.articles, self.wrappers, self.resolved, self.writer.manifest,
                                  self.rules, plan.order)  # fmt: skip
        report.order = plan.order.name if plan else None
        limit = min(pages, PAGES)  # once, for both ways of choosing: the cap is never exceeded on either
        todo = queue.candidates(today, limit, report) if queue else self._candidates(today, limit, report)
        material = queue.material_keys if queue else set()
        for number, (key, url) in enumerate(todo):
            if self.clock() - started >= budget:
                report.counts["budget_stopped"] = len(todo) - number
                break
            report.counts["material_asked"] += key in material
            self._read(key, url, today, apply, report, budget - (self.clock() - started))
        self._check_reader(report)
        if apply and plan and plan.note:
            self._write_note(
                replace(
                    plan.note,
                    scored=report.counts["scored"],
                    material=report.counts["material"],
                    asked=report.counts["asked"],
                ),
                moment,
                report,
            )
        return report

    def _write_note(self, note, moment: datetime, report: ReadReport) -> None:
        """The pass note (NP8): one write-once file with the versions used; a failure is counted by its code."""
        try:
            self.notes.write(note, moment)
        except RawFileConflict:
            report.reject(codes.READ_CONFLICT)
        except Exception:  # noqa: BLE001 - Drive's own errors may name paths; only the code is kept
            report.reject(codes.READ_WRITE_FAILED)

    def _ready(self, report: ReadReport, apply: bool) -> bool:
        skipped = self.articles.skipped + self.wrappers.skipped + self.resolved.skipped + self.writer.skipped_rows
        skipped += self.notes.skipped_rows if self.notes else 0
        if skipped:
            report.reject(codes.MANIFEST_ROW_SKIPPED, skipped)
        if apply:
            try:
                self.writer.check_ready()
                if self.notes:
                    self.notes.check_ready()
            except TableFileBroken:
                report.reject(codes.MANIFEST_BROKEN)
        return report.ok

    def _candidates(self, today: date, pages: int, report: ReadReport) -> list[tuple[str, str]]:
        oldest = today - timedelta(days=LOOKBACK_DAYS)
        newest_first = sorted(self.articles.recorded_on.items(), key=lambda kv: (kv[1], kv[0]), reverse=True)
        found: list[tuple[str, str]] = []
        for key, recorded in newest_first:
            day = date.fromisoformat(recorded)
            if day < oldest:
                break
            if key in self.writer.manifest.recorded:
                report.counts["already"] += 1
            elif len(found) >= pages:
                break
            elif report.counts["examined"] >= MAX_RECORD_READS:
                report.counts["unexamined"] += 1
            else:
                url = self._page_url(key, report)
                if url:
                    found.append((key, url))
        return found

    def _page_url(self, key: str, report: ReadReport) -> str:
        """The page to read for an article, or "" (counted why)."""
        report.counts["examined"] += 1
        if key in self.wrappers.recorded:
            if key not in self.resolved.recorded:
                report.counts["unresolved"] += 1
                return ""
            data = self.record.get(resolution_path(key))
            url = parse_resolution(data).url if data else ""
        else:
            data = self.record.get(article_path(key))
            url = article_from_bytes(data).canonical_url if data else ""
        if not url:
            report.counts["no_link"] += 1
        elif not fetchable(self.rules, url):
            report.counts["unlisted"] += 1  # not an outlet we may read: no request is made
            return ""
        return url

    def _read(self, key: str, url: str, today: date, apply: bool, report: ReadReport, budget_left: float) -> None:
        report.counts["asked"] += 1
        page = self.fetcher.fetch(url, max(1.0, budget_left))
        report.pages[page.code] += 1
        if page.code != model.OK:
            return
        try:
            facts = extract(page.body)
        except Exception:  # noqa: BLE001 - one hostile page must never stop the run (judge 89): counted, then on
            report.pages["extract_error"] += 1
            return
        if facts is None:
            report.pages["no_facts"] += 1
            return
        if not apply:
            report.pages["would_write"] += 1
            return
        read = build_read(key, plain_host(urlsplit(page.final_url).hostname), facts)
        try:
            outcome = self.writer.write(read_path(key), read.to_bytes(), today)
            report.pages["written" if outcome is Written.NEW else "no_op"] += 1
        except RawFileConflict:
            report.reject(codes.READ_CONFLICT)
        except Exception:  # noqa: BLE001 - Drive's own errors may name paths; only the code is kept
            report.reject(codes.READ_WRITE_FAILED)

    @staticmethod
    def _check_reader(report: ReadReport) -> None:
        """Loud (red, alerted): the pages asked for were refused or failed, so a blocked runner is never a green run."""
        faults = sum(n for code, n in report.pages.items() if code in model.CODES and code not in NOT_A_FAULT)
        ok = report.pages[model.OK]
        if (faults and ok == 0 and faults >= NOTHING_OK_MIN_ASKED) or (
            faults >= FAILING_MIN_ASKED and ok / faults < FAILING_BELOW_SHARE
        ):
            report.reject(codes.READER_FAILING)
