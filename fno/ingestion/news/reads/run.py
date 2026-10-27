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
from datetime import date, timedelta
from urllib.parse import urlsplit

from fno.ingestion.news import codes
from fno.ingestion.news.article.article_file import article_from_bytes
from fno.ingestion.news.pages import model
from fno.ingestion.news.pages.model import PageFetcher
from fno.ingestion.news.reads.extract import extract
from fno.ingestion.news.reads.read_file import build_read, read_path
from fno.ingestion.news.reads.report import ReadReport
from fno.ingestion.news.record.manifest import NewsManifest
from fno.ingestion.news.record.planner import article_path
from fno.ingestion.news.resolve.resolution_file import parse_resolution, resolution_path
from fno.ingestion.news.sources.rules import SourceRules, plain_host
from fno.ingestion.news.write_once import WriteOnceWriter, Written
from fno.ingestion.storage.raw_store import RawFileConflict, RawFileStore
from fno.ingestion.storage.row_log import TableFileBroken

LOOKBACK_DAYS = 3
PAGES = 80
MAX_RECORD_READS = 400
BUDGET_SECONDS = 900.0
FAILING_MIN_ASKED, FAILING_BELOW_SHARE, NOTHING_OK_MIN_ASKED = 10, 0.5, 3
NOT_A_FAULT = (model.ROBOTS_DISALLOWED, model.HOST_STOPPED, model.HOST_NOT_ALLOWED)  # expected, not a failing reader


class ReadPass:
    def __init__(self, record: RawFileStore, articles: NewsManifest, wrappers: NewsManifest, resolved: NewsManifest,
                 fetcher: PageFetcher, rules: SourceRules, writer: WriteOnceWriter,
                 clock: Callable[[], float]):  # fmt: skip
        """`record`: the Record, read only. `articles`, `wrappers`, `resolved`: the three manifests of the checkout.
        `writer`: the only way to write, with the reads manifest. `clock`: monotonic seconds, for the run budget."""
        self.record, self.articles, self.wrappers, self.resolved = record, articles, wrappers, resolved
        self.fetcher, self.rules, self.writer, self.clock = fetcher, rules, writer, clock

    def run(self, today: date, apply: bool, pages: int = PAGES, budget: float = BUDGET_SECONDS) -> ReadReport:
        report = ReadReport(apply)
        started = self.clock()
        if not self._ready(report, apply):
            return report
        todo = self._candidates(today, min(pages, PAGES), report)
        for number, (key, url) in enumerate(todo):
            if self.clock() - started >= budget:
                report.counts["budget_stopped"] = len(todo) - number
                break
            self._read(key, url, today, apply, report)
        self._check_reader(report)
        return report

    def _ready(self, report: ReadReport, apply: bool) -> bool:
        skipped = self.articles.skipped + self.wrappers.skipped + self.resolved.skipped + self.writer.skipped_rows
        if skipped:
            report.reject(codes.MANIFEST_ROW_SKIPPED, skipped)
        if apply:
            try:
                self.writer.check_ready()
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
        elif not self.rules.may_fetch(plain_host(urlsplit(url).hostname)):
            report.counts["unlisted"] += 1  # not an outlet we may read: no request is made
            return ""
        return url

    def _read(self, key: str, url: str, today: date, apply: bool, report: ReadReport) -> None:
        report.counts["asked"] += 1
        page = self.fetcher.fetch(url)
        report.pages[page.code] += 1
        if page.code != model.OK:
            return
        facts = extract(page.body)
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
