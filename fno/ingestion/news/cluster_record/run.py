"""One cluster run (P2d): read the Record's recent articles and the earlier run's file (neither changes), cluster them
with P2c, check the clusters account for every article read, and only then write the cluster file. Anything that does
not add up writes nothing and says why in a fixed code.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from fno.ingestion.news import codes
from fno.ingestion.news.article.article_file import Article
from fno.ingestion.news.cluster import cluster as clustering_module
from fno.ingestion.news.cluster.cluster import Clustering, cluster_articles
from fno.ingestion.news.cluster_record.article_source import ArticleSource
from fno.ingestion.news.cluster_record.cluster_file import (
    ClusterFile,
    cluster_file_bytes,
    cluster_folder,
    cluster_path,
    parse_cluster_file,
    window_end_of,
)
from fno.ingestion.news.cluster_record.grouping import GroupingBlocked, SymbolGrouping
from fno.ingestion.news.cluster_record.report import ClusterReport
from fno.ingestion.news.cluster_record.writer import ClusterWriter
from fno.ingestion.storage.raw_store import RawFileConflict, RawFileStore
from fno.ingestion.storage.row_log import TableFileBroken


def reconciles(clustering: Clustering, articles: tuple[Article, ...]) -> bool:
    """Every cluster member is an article that was read, none is in two clusters, and clustered plus outside-the-window
    articles are exactly the distinct articles read."""
    members = [key for cluster in clustering.clusters for key in cluster.member_keys]
    read = {article.key for article in articles}
    return (
        len(members) == len(set(members))
        and set(members) <= read
        and clustering.clustered + clustering.outside_window == len(read)
    )


class ClusterRun:
    def __init__(
        self, source: ArticleSource, writer: ClusterWriter, record: RawFileStore, grouping: SymbolGrouping | None = None
    ):
        """`record`: the Record area, read only here (the earlier run's file); the writer is the only way to write.
        `grouping`: algorithm version 2's inputs (NP6a); None runs version 1, exactly as before."""
        self.source, self.writer, self.record, self.grouping = source, writer, record, grouping

    def run(self, as_of: datetime) -> ClusterReport:
        report = ClusterReport()
        try:
            self.writer.check_ready()
        except TableFileBroken:
            report.reject(codes.MANIFEST_BROKEN)
            return report
        for skipped in (self.source.skipped_rows, self.writer.skipped_rows):
            if skipped:  # a not-whole manifest row may hide an article or a file: report it, write nothing
                report.reject(codes.MANIFEST_ROW_SKIPPED, skipped)
        found = self.source.candidates(as_of)
        report.read(len(found.articles), found.unreadable)
        try:
            earlier = self._previous_file(as_of)
            previous = earlier.clusters if earlier else ()
            inputs = self.grouping.inputs(found.articles, as_of, earlier) if self.grouping else None
        except ValueError:
            report.reject(codes.PREVIOUS_UNREADABLE)
            return report
        except GroupingBlocked as blocked:  # no company list is fine; a list that cannot be read stops the run
            report.reject(str(blocked))
            return report
        clustering = cluster_articles(found.articles, as_of, previous, preparer=inputs.preparer if inputs else None)
        if inputs:
            clustering = replace(
                clustering,
                companies_version=inputs.companies_version,
                resolutions_used=inputs.resolutions_used,
                companies_sha256=inputs.companies_sha256,
            )
        report.clustered(clustering)
        if not reconciles(clustering, found.articles):
            report.reject(codes.CLUSTER_NOT_RECONCILED)
        if report.ok:
            self._write(clustering, report)
        return report

    def _previous_file(self, as_of: datetime) -> ClusterFile | None:
        """The latest earlier file of this version (ValueError when that file is damaged)."""
        version = self.grouping.version if self.grouping else clustering_module.ALGORITHM_VERSION
        folder = cluster_folder(version)
        earlier = [
            (end, name) for name in self.record.checksums(folder) if (end := window_end_of(name)) and end < as_of
        ]
        if not earlier:
            return None
        data = self.record.get(f"{folder}/{max(earlier)[1]}")
        if data is None:
            raise ValueError("listed but unreadable")
        return parse_cluster_file(data)

    def _write(self, clustering: Clustering, report: ClusterReport) -> None:
        try:
            report.written(
                self.writer.write(
                    cluster_path(clustering.algorithm_version, clustering.as_of),
                    cluster_file_bytes(clustering),
                    clustering.as_of.date(),
                )
            )
        except RawFileConflict:
            report.reject(codes.CLUSTER_CONFLICT)
        except Exception:  # noqa: BLE001 - Drive's own errors may name paths; only the code is kept
            report.reject(codes.CLUSTER_RECORD_FAILED)
