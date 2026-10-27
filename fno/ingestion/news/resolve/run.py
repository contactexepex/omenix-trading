"""One resolve pass (NP2c; NP0 section 2b): over the Record, not over Staging. It reads the articles manifest of the
last `LOOKBACK_DAYS` days newest first, reads each article (read only), and for the wrapper articles that have no
resolution yet asks the resolver, ONCE per run with up to `CAP` links, and writes each success as a write-once file.
A failure writes nothing and is counted; the link is tried again on the next pass until it leaves the look-back, so the
staging cleanup trashing a promoted poll after 7 days loses nothing the pass needs.

Bounded by construction: at most `CAP` links resolved and at most `MAX_READS` article files read per pass, the rest
counted (`backlog`: wrapper articles beyond the cap; `unexamined`: not read at all). `expiring` counts unresolved
wrapper articles on the last day of the look-back, about to be left unresolved for good, and is alerted. Without
`apply` the pass still asks the resolver (that is the probe) but writes nothing."""

from __future__ import annotations

from datetime import date, timedelta

from fno.ingestion.news import codes
from fno.ingestion.news.article.article_file import Article, article_from_bytes
from fno.ingestion.news.article.keys import WRAPPER
from fno.ingestion.news.record.manifest import NewsManifest
from fno.ingestion.news.record.planner import article_path
from fno.ingestion.news.resolve.model import BAD_RESULT, RESOLVED, LinkResolver, Resolved
from fno.ingestion.news.resolve.report import ResolveReport
from fno.ingestion.news.resolve.resolution_file import build_resolution, resolution_path
from fno.ingestion.news.write_once import WriteOnceWriter, Written
from fno.ingestion.storage.raw_store import RawFileConflict, RawFileStore
from fno.ingestion.storage.row_log import TableFileBroken

LOOKBACK_DAYS = 3
CAP = 80  # links per pass: about 53 a pass are needed to keep up with ~1,280 a day at 1.5 s apart
MAX_READS = 600  # article files read per pass
FAILING_MIN_ASKED, FAILING_BELOW_SHARE, NOTHING_RESOLVED_MIN_ASKED = (
    10,
    0.5,
    3,
)  # a batch this big with fewer than half resolved is a failing service


class ResolvePass:
    unresolved_last_day = 0  # wrapper articles on the last look-back day that the cap left out of this pass

    def __init__(self, record: RawFileStore, articles: NewsManifest, resolver: LinkResolver, writer: WriteOnceWriter):
        """`record`: the Record, read only. `articles`: the articles manifest. `resolver`: ONE per run (its stop and
        its pacing live in it). `writer`: the only way to write, with the resolved-files manifest."""
        self.record, self.articles, self.resolver, self.writer = record, articles, resolver, writer

    def run(self, today: date, apply: bool, cap: int = CAP) -> ResolveReport:
        report = ResolveReport(apply)
        if not self._ready(report, apply):
            return report
        self.unresolved_last_day = 0
        pending = self._pending(today, min(cap, CAP), report)
        report.counts["pending"] = len(pending)
        answers: list[Resolved] = []
        if pending:
            answers = self.resolver.resolve([article.wrapper_link for article, _ in pending])
            for (article, _), answer in zip(pending, answers, strict=True):
                self._record_answer(article, answer, today, apply, report)
            self._check_service(len(pending), report)
        report.counts["expiring"] = self._expiring(today, pending, answers)
        return report

    @staticmethod
    def _check_service(asked: int, report: ResolveReport) -> None:
        """Loud (red and alerted): a resolver that resolves nothing of three or more links, or under half of a batch of
        ten or more. A broken decoder, a blocked runner or a pushing-back service must never finish green while links
        age out unresolved; one or two dead links are not a failing service."""
        resolved = report.results[RESOLVED]
        nothing = resolved == 0 and asked >= NOTHING_RESOLVED_MIN_ASKED
        if nothing or (asked >= FAILING_MIN_ASKED and resolved / asked < FAILING_BELOW_SHARE):
            report.reject(codes.RESOLVER_FAILING)

    def _ready(self, report: ResolveReport, apply: bool) -> bool:
        if self.writer.skipped_rows or self.articles.skipped:
            report.reject(codes.MANIFEST_ROW_SKIPPED, self.writer.skipped_rows + self.articles.skipped)
        if apply:
            try:
                self.writer.check_ready()
            except TableFileBroken:
                report.reject(codes.MANIFEST_BROKEN)
        return report.ok

    def _pending(self, today: date, cap: int, report: ResolveReport) -> list[tuple[Article, date]]:
        """Wrapper articles of the look-back with no resolution yet, newest first, at most `cap` (rest: `backlog`)."""
        oldest = today - timedelta(days=LOOKBACK_DAYS)
        newest_first = sorted(self.articles.recorded_on.items(), key=lambda kv: (kv[1], kv[0]), reverse=True)
        found: list[tuple[Article, date]] = []
        for key, recorded in newest_first:
            day = date.fromisoformat(recorded)
            if day < oldest:
                break
            if key in self.writer.manifest.recorded:
                report.counts["already"] += 1
            elif report.counts["examined"] >= MAX_READS:
                report.counts["unexamined"] += 1
                if day == oldest:  # unread, so unknown: counted as expiring rather than hidden by the read cap
                    self.unresolved_last_day += 1
            else:
                self._consider(key, day, cap, found, report, oldest)
        return found

    def _consider(self, key, day, cap, found, report, oldest) -> None:
        report.counts["examined"] += 1
        try:
            article = article_from_bytes(self.record.get(article_path(key)))
        except Exception:  # noqa: BLE001 - a missing file (None) or a damaged one: counted, nothing is named
            report.reject(codes.ARTICLE_UNREADABLE)
            return
        if article.kind != WRAPPER or not article.wrapper_link:
            report.counts["not_wrapper"] += 1
        elif len(found) < cap:
            found.append((article, day))
        else:
            report.counts["backlog"] += 1
            if day == oldest:
                self.unresolved_last_day += 1

    def _expiring(self, today: date, pending, answers) -> int:
        oldest = today - timedelta(days=LOOKBACK_DAYS)
        failed = sum(1 for (_, day), a in zip(pending, answers, strict=True) if day == oldest and a.code != RESOLVED)
        return self.unresolved_last_day + failed

    def _record_answer(
        self, article: Article, answer: Resolved, today: date, apply: bool, report: ResolveReport
    ) -> None:
        resolution = build_resolution(article, answer.url) if answer.code == RESOLVED else None
        if answer.code == RESOLVED and resolution is None:
            report.results[BAD_RESULT] += 1
            return
        report.results[answer.code] += 1
        if resolution is None:
            return
        if not apply:
            report.results["would_write"] += 1
            return
        try:
            outcome = self.writer.write(resolution_path(article.key), resolution.to_bytes(), today)
            report.results["written" if outcome is Written.NEW else "no_op"] += 1
        except RawFileConflict:
            report.reject(codes.RESOLUTION_CONFLICT)
        except Exception:  # noqa: BLE001 - Drive's own errors may name paths; only the code is kept
            report.reject(codes.RESOLUTION_WRITE_FAILED)
