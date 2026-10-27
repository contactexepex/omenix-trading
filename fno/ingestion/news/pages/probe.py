"""The outlet probe (NP4a; NP0 section 2d): one front-page request to each listed outlet, from wherever it runs, so the
owner sees which outlets a GitHub runner can really reach before any outlet is marked fetchable. Agentic's `fetch:
false` list was measured from another network. The allowlist is public, so a domain and its fixed result code may be
printed; no URL beyond the domain, no page content and no header is ever kept. Fetchable outlets are probed through
the ordinary fetcher (robots.txt, address check, 1.5 s spacing, host stop). The outlets that refuse automated reads
are probed only when asked (`include_refusing`): one polite request each, still through every guard except the `fetch:
false` flag itself; the result is a report for the owner, and the allowlist file is never edited by a job."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field

from fno.ingestion.news.pages.model import OK, PageFetcher
from fno.ingestion.news.sources.rules import SourceRules


@dataclass
class ProbeReport:
    results: list[tuple[str, bool, str]] = field(default_factory=list)  # (domain, refuses automated reads, code)

    def counts(self) -> Counter[str]:
        return Counter(code for _, _, code in self.results)

    def line(self) -> str:
        done = ", ".join(f"{code} {n}" for code, n in sorted(self.counts().items())) or "no outlets"
        return f"news probe-outlets: {len(self.results)} outlets, {done}"

    @staticmethod
    def line_of(row: tuple[str, bool, str]) -> str:
        domain, refuses, code = row
        return f"{domain}{' (fetch: false)' if refuses else ''}: {code}"

    def outlet_lines(self) -> list[str]:
        return [self.line_of(row) for row in self.results]

    @property
    def reachable(self) -> int:
        return self.counts()[OK]


def probe_outlets(
    rules: SourceRules, fetcher: PageFetcher, include_refusing: bool, on_result: Callable[[str], None] | None = None
) -> ProbeReport:
    """`on_result`: called with each outlet's line as soon as it is known, so a run that is killed (a dropped runner,
    the job timeout) still leaves the results so far in the log (judge 87)."""
    report = ProbeReport()
    listed = [(domain, not rules.may_fetch(domain)) for domain in sorted(rules.outlets)]
    for domain, refuses in sorted(listed, key=lambda row: row[1]):  # fetchable outlets first
        if refuses and not include_refusing:
            continue
        report.results.append((domain, refuses, fetcher.fetch(f"https://{domain}/").code))
        if on_result is not None:
            on_result(report.line_of(report.results[-1]))
    return report
