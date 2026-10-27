"""What one `news cluster` run did: counts and fixed codes only (invariant 1 of P2), never a title, URL, key or id."""

from __future__ import annotations

from collections import Counter

from fno.ingestion.news import codes
from fno.ingestion.news.cluster.cluster import Clustering
from fno.ingestion.news.cluster.prepare import GROUPER_VERSION
from fno.ingestion.news.cluster_record.writer import Written

NOT_WRITTEN = "not_written"
COUNTS = ("articles", "clusters", "clustered", "outside_window", "repeated_keys")
URL_COUNTS = (  # version 2 only; companies_version 0 means no company list was read (shown so a mistake is visible)
    "url_joins", "url_joins_refused", "url_joins_unlike_title", "resolutions_used", "companies_version",
)  # fmt: skip
CONFLICT_ALERT = (
    "cluster_conflict: the closed window's cluster file exists with other bytes; the inputs, the algorithm "
    "version or the determinism changed for that window: investigate, nothing was overwritten"
)


class ClusterReport:
    def __init__(self) -> None:
        self.counts: Counter[str] = Counter()
        self.rejected: Counter[str] = Counter()
        self.outcome = NOT_WRITTEN

    def reject(self, code: str, number: int = 1) -> None:
        self.rejected[code] += number

    def read(self, articles: int, unreadable: int) -> None:
        self.counts["articles"] = articles
        if unreadable:
            self.reject(codes.ARTICLE_UNREADABLE, unreadable)

    def clustered(self, clustering: Clustering) -> None:
        self.counts["clusters"] = len(clustering.clusters)
        self.counts["clustered"] = clustering.clustered
        self.counts["outside_window"] = clustering.outside_window
        self.counts["repeated_keys"] = clustering.repeated_keys
        if clustering.algorithm_version == GROUPER_VERSION:
            for name in URL_COUNTS:
                self.counts[name] = getattr(clustering, name)

    def written(self, outcome: Written) -> None:
        self.outcome = outcome.value

    @property
    def ok(self) -> bool:
        return not self.rejected

    def line(self) -> str:
        done = ", ".join(f"{k} {self.counts[k]}" for k in (*COUNTS, *(u for u in URL_COUNTS if u in self.counts)))
        stuck = "".join(f", {code} {n}" for code, n in sorted(self.rejected.items()))
        return f"news cluster: {done}, {self.outcome}{stuck}"

    def alert_text(self) -> str:
        return CONFLICT_ALERT if codes.CLUSTER_CONFLICT in self.rejected else self.line()
