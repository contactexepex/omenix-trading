"""The material-first way of choosing the pages of a pass (NP8).

Two phases inside ONE budget of Record reads, so the cap means one thing: `SCORE_READS` article files are read (the
newest unread articles) and ranked by the `ReadOrder`; then the page of each ranked article is found, a Google News item
needing a resolution file, at most `RESOLVE_READS` of them. Together at most `MAX_RECORD_READS` Record files. Down the
ranking until `pages` are found. What the ranking cannot reach is counted: articles beyond the scored slice
(`unexamined`), Google News items left without a resolution read (`resolve_reads_exhausted`). Counts only, as
everywhere in the pass."""

from __future__ import annotations

from datetime import date, timedelta

from fno.ingestion.news.article.article_file import article_from_bytes
from fno.ingestion.news.reads.limits import LOOKBACK_DAYS, RESOLVE_READS, SCORE_READS
from fno.ingestion.news.reads.links import fetchable
from fno.ingestion.news.reads.order import ReadOrder, Scored
from fno.ingestion.news.reads.report import ReadReport
from fno.ingestion.news.record.manifest import NewsManifest
from fno.ingestion.news.record.planner import article_path
from fno.ingestion.news.resolve.resolution_file import parse_resolution, resolution_path
from fno.ingestion.news.sources.rules import SourceRules
from fno.ingestion.storage.raw_store import RawFileStore


class MaterialQueue:
    def __init__(self, record: RawFileStore, articles: NewsManifest, wrappers: NewsManifest, resolved: NewsManifest,
                 read: NewsManifest, rules: SourceRules, order: ReadOrder):  # fmt: skip
        """`read`: the reads manifest (articles already read are skipped)."""
        self.record, self.articles, self.wrappers, self.resolved = record, articles, wrappers, resolved
        self.read, self.rules, self.order = read, rules, order
        self.material_keys: set[str] = set()

    def candidates(self, today: date, pages: int, report: ReadReport) -> list[tuple[str, str]]:
        scored = self._score(today, report)
        ranked, material = self.order.rank(scored)
        report.counts["material"] = material
        self.material_keys = {article.key for article in ranked[:material]}
        return self._pages(ranked, pages, report)

    def _score(self, today: date, report: ReadReport) -> list[Scored]:
        oldest = today - timedelta(days=LOOKBACK_DAYS)
        scored: list[Scored] = []
        for key, recorded in sorted(self.articles.recorded_on.items(), key=lambda kv: (kv[1], kv[0]), reverse=True):
            if date.fromisoformat(recorded) < oldest:
                break
            if key in self.read.recorded:
                report.counts["already"] += 1
            elif len(scored) >= SCORE_READS:
                report.counts["unexamined"] += 1
            else:
                report.counts["examined"] += 1
                data = self.record.get(article_path(key))
                if not data:
                    report.counts["no_link"] += 1
                    continue
                article = article_from_bytes(data)
                scored.append(
                    Scored(key, article.title, article.source, article.canonical_url, key in self.wrappers.recorded)
                )
        report.counts["scored"] = len(scored)
        return scored

    def _pages(self, ranked: list[Scored], pages: int, report: ReadReport) -> list[tuple[str, str]]:
        found: list[tuple[str, str]] = []
        for article in ranked:
            if len(found) >= pages:
                break
            url = self._page_url(article, report)
            if not url:
                continue
            if fetchable(self.rules, url):
                found.append((article.key, url))
            else:
                report.counts["unlisted"] += 1  # not an outlet we may read: no request is made
        return found

    def _page_url(self, article: Scored, report: ReadReport) -> str:
        if not article.wrapper:
            return article.link or self._none(report)
        if article.key not in self.resolved.recorded:
            report.counts["unresolved"] += 1
            return ""
        if report.counts["resolve_reads"] >= RESOLVE_READS:
            # skipped for lack of a read; a publisher item may still follow
            report.counts["resolve_reads_exhausted"] += 1
            return ""
        report.counts["resolve_reads"] += 1
        data = self.record.get(resolution_path(article.key))
        return (parse_resolution(data).url if data else "") or self._none(report)

    @staticmethod
    def _none(report: ReadReport) -> str:
        report.counts["no_link"] += 1
        return ""
