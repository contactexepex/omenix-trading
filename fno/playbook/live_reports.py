"""Where the live-feature gate (B7) gets each live feature's validation report. The committed reports are written by
`python -m fno research validate-live`; `RecomputedLiveReports` closes judge 44's follow-up: the gate decides on a fresh
recomputation over every recorded day, so neither an edited nor a removed day in a committed report can change the
verdict (judge 67). The committed report must still exist and agree with the recomputation on every day it holds: it is
the record the red team reads."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping
from pathlib import Path

from ..research_engine.live_gate import reports_from_folder


class LiveReports(ABC):
    @abstractmethod
    def report(self, live_feature: str) -> Mapping | None:
        """The feature's validation report (B7 summary with per-day `comparisons`), or None if there is none."""


class CommittedLiveReports(LiveReports):
    def __init__(self, folder: Path):
        self.folder = folder

    def report(self, live_feature: str) -> Mapping | None:
        return reports_from_folder(self.folder).get(live_feature)


class RecomputedLiveReports(LiveReports):
    """The fresh recomputation (all recorded days), when a committed report exists and is exactly its first rows: the
    same days in order, no gap, every value equal; only days recorded after the report may follow. A strategy whose live
    feature stops agreeing on later days stops passing the gate: it no longer trades what was tested."""

    def __init__(self, committed: LiveReports, recompute: Callable[[str], Mapping]):
        self.committed, self.recompute = committed, recompute

    def report(self, live_feature: str) -> Mapping | None:
        report = self.committed.report(live_feature)
        if report is None:
            return None
        recomputed = self.recompute(live_feature)
        rows = list(report["comparisons"])
        return recomputed if rows == list(recomputed["comparisons"])[: len(rows)] else None
