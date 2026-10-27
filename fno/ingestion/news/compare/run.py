"""One clustering comparison (NP3c): the same recent articles clustered with algorithm version 1 and 2, in memory,
and counted. **Read only**: it has no writer, no manifest and no Drive write path (it is built from a read-only
article source and the version 2 grouping, which reads the Record and the private company list); it commits nothing
and sends no alert. The result is one line of counts per kind. Version 2's company-list pin against the last file is
not applied here (nothing is written, so there is nothing to protect); a list that cannot be read still stops the
comparison with its code."""

from __future__ import annotations

from collections import Counter
from datetime import datetime

from fno.ingestion.news import codes
from fno.ingestion.news.cluster.cluster import cluster_articles
from fno.ingestion.news.cluster_record.article_source import ArticleSource
from fno.ingestion.news.cluster_record.grouping import GroupingBlocked, SymbolGrouping
from fno.ingestion.news.compare import metrics


class ComparisonReport:
    def __init__(self) -> None:
        self.lines: list[str] = []
        self.rejected: Counter[str] = Counter()

    @property
    def ok(self) -> bool:
        return not self.rejected

    def line(self) -> str:
        stuck = "".join(f", {code} {n}" for code, n in sorted(self.rejected.items()))
        return "\n".join(self.lines) + (f"\nnews compare-clusterings stopped{stuck}" if stuck else "")


class ComparisonRun:
    def __init__(self, source: ArticleSource, grouping: SymbolGrouping):
        self.source, self.grouping = source, grouping

    def run(self, as_of: datetime) -> ComparisonReport:
        report = ComparisonReport()
        found = self.source.candidates(as_of)
        if found.unreadable:
            report.rejected[codes.ARTICLE_UNREADABLE] = found.unreadable
        try:
            inputs = self.grouping.inputs(found.articles, as_of)
        except GroupingBlocked as blocked:
            report.rejected[str(blocked)] += 1
        if not report.ok:
            return report
        first = cluster_articles(found.articles, as_of)
        second = cluster_articles(found.articles, as_of, preparer=inputs.preparer)
        report.lines += [_shape_line("v1", first), _shape_line("v2", second), _crossing_line(first, second)]
        report.lines.append(
            f"v2 inputs: url_joins {second.url_joins}, url_joins_refused {second.url_joins_refused}, "
            f"url_joins_unlike_title {second.url_joins_unlike_title}, companies_version {inputs.companies_version}, "
            f"resolutions_used {inputs.resolutions_used}"
        )
        report.lines.append(_coverage_line(metrics.coverage(found.articles, inputs.preparer.tagger)))
        return report


def _shape_line(name: str, clustering) -> str:
    shape = metrics.shape_of(clustering)
    sizes = " ".join(f"{low}-{high}:{n}" for (low, high), n in zip(metrics.SIZE_BUCKETS, shape.sizes, strict=True))
    return (
        f"{name}: clustered {clustering.clustered}, clusters {shape.clusters}, singletons {shape.singletons}, "
        f"largest {shape.largest}, sizes {sizes}"
    )


def _crossing_line(first, second) -> str:
    cross = metrics.crossing(first, second)
    return (
        f"v1 vs v2: v2_clusters_merging_v1_clusters {cross.merged_by_second}, "
        f"v1_clusters_split_by_v2 {cross.split_by_second}"
    )


def _coverage_line(cover: metrics.Coverage) -> str:
    counts = " ".join(
        f">={t}:{n}" for t, n in zip(metrics.COMPANY_THRESHOLDS, cover.companies_with_at_least, strict=True)
    )
    return (
        f"tags: articles {cover.articles}, tagged {cover.tagged}, tagged_high {cover.tagged_high}, "
        f"companies_seen {counts}"
    )
