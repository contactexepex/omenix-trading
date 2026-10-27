"""The recall report (NP11): of the articles that name a company, how many did the broad feeds find alone, the targeted
per-company queries alone, or both. **Read only and counts only**: it has no writer and no manifest, commits nothing and
sends no alert; no feed id, key, company, symbol or title is ever returned or printed (a whitelist test reads every word
of the output). "Both" proves overlap, not what a feed would have missed. An article recorded before provenance existed
is counted as `no_provenance`, and one found by a feed the list does not label is counted under `unknown`."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta

from fno.ingestion.news import codes
from fno.ingestion.news.cluster_record.grouping import GroupingBlocked
from fno.ingestion.news.provenance.index import ProvenanceUnreadable
from fno.ingestion.news.provenance.model import BROAD, TARGETED, UNKNOWN, Pair

BUCKETS = ("broad_only", "targeted_only", "both", "unknown_only", "no_provenance")
DEFAULT_DAYS = 14


class RecallReport:
    def __init__(self) -> None:
        self.counts: Counter[str] = Counter()
        self.rejected: Counter[str] = Counter()
        self.days = 0

    @property
    def ok(self) -> bool:
        return not self.rejected

    def line(self) -> str:
        if self.rejected:
            stuck = "".join(f", {code} {n}" for code, n in sorted(self.rejected.items()))
            return f"news provenance-recall stopped{stuck}"
        buckets = ", ".join(f"{name} {self.counts[name]}" for name in BUCKETS)
        return (
            f"recall: window_days {self.days}, tagged {self.counts['tagged']}, {buckets}, "
            f"with_unknown_feed {self.counts['with_unknown_feed']}"
        )


def bucket_of(pairs: frozenset[Pair]) -> str:
    """Exactly one bucket per article, from the scopes of the feeds that found it."""
    scopes = {scope for _, scope in pairs}
    if not scopes:
        return "no_provenance"
    if BROAD in scopes and TARGETED in scopes:
        return "both"
    if BROAD in scopes:
        return "broad_only"
    if TARGETED in scopes:
        return "targeted_only"
    return "unknown_only"


class RecallRun:
    def __init__(self, source, grouping, index):
        """`source`: the read-only article source; `grouping`: gives the tagger (the company list, read only);
        `index`: the provenance files, read only."""
        self.source, self.grouping, self.index = source, grouping, index

    def run(self, as_of: datetime, days: int = DEFAULT_DAYS) -> RecallReport:
        report = RecallReport()
        report.days = days
        found = self.source.candidates(as_of, timedelta(days=days + 2))
        if found.unreadable:
            report.rejected[codes.ARTICLE_UNREADABLE] = found.unreadable
        try:
            tagger = self.grouping.inputs(found.articles, as_of).preparer.tagger
            held = self._held(as_of.date(), days)
        except GroupingBlocked as blocked:
            report.rejected[str(blocked)] += 1
        except ProvenanceUnreadable:
            report.rejected[codes.PROVENANCE_UNREADABLE] += 1
        if not report.ok:
            return report
        for article in found.articles:
            if not tagger.tag(article.title, None, article.source).symbols:
                continue
            pairs = held.get(article.key, frozenset())
            report.counts["tagged"] += 1
            report.counts[bucket_of(pairs)] += 1
            report.counts["with_unknown_feed"] += any(scope == UNKNOWN for _, scope in pairs)
        if report.counts["tagged"] != sum(report.counts[name] for name in BUCKETS):
            report.rejected[codes.NOT_RECONCILED] += 1
        return report

    def _held(self, last_day, days: int) -> dict[str, frozenset[Pair]]:
        merged: dict[str, set[Pair]] = {}
        for back in range(days + 3):
            for key, pairs in self.index.pairs(last_day - timedelta(days=back)).items():
                merged.setdefault(key, set()).update(pairs)
        return {key: frozenset(pairs) for key, pairs in merged.items()}
