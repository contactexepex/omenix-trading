"""Story G11 C17, what the AI books' v4 runs cost, printed by `ai collect --protocol v4`: per book, the runs since the
books' v4 go-live, their minutes as BG1's ledger holds them (what BG1's cap counts: working minutes once BG1-w reads
`sealed_at`, owner 24 Oct; start to end before it), and from each
run's own timing file (`run_timing.py`) the working minutes (start to seal), the waiting minutes (seal to the end,
mostly the wait for 15:10:10) and the reveal calls (turns) the wait took. p50 and p95 are nearest-rank. A run whose
file has no seal time counts as "working unknown", never as zero. Whether the waiting minutes count against BG1's cap
is the owner's to rule (orchestrator, 24 Oct): this report shows them apart so the ruling can be made on numbers."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from ..budget.usage_ledger import UsageLedger
from ..constants import AI_BOOKS
from ..research_engine.statistics import nearest_rank
from .paths import AI_FOLDER

LINE = "Omenix F&O AI v4 cost (BG1): {book}: {result}"
TIMING_SUFFIX = ".timing.json"


@dataclass
class V4CostReport:
    root: Path
    ledger: UsageLedger
    live_from: date | None

    def lines(self) -> list[str]:
        if self.live_from is None:
            return []
        return [LINE.format(book=book, result=self._book(book)) for book in AI_BOOKS]

    def _book(self, book: str) -> str:
        minutes = [float(r["minutes"]) for r in self.ledger.rows() if r["book"] == book and self._v4(r["date"])]
        runs = self._timings(book)
        if not minutes and not runs:
            return "no v4 runs yet"
        working = [_minutes(t["started_at"], t["sealed_at"]) for t in runs if t.get("sealed_at")]
        waiting = [_minutes(t["sealed_at"], t["ended_at"]) for t in runs if t.get("sealed_at")]
        calls = [float(t["reveal_calls"]) for t in runs if t.get("reveal_calls") is not None]
        unknown = len(runs) - len(working)
        parts = [f"{len(minutes)} run(s) in BG1's ledger, minutes {_spread(minutes)}", f"working {_spread(working)}",
                 f"waiting {_spread(waiting)}", f"reveal calls {_spread(calls)}"]  # fmt: skip
        return "; ".join(parts) + (f"; working unknown on {unknown} run(s) (no seal time)" if unknown else "")

    def _timings(self, book: str) -> list[dict]:
        found = []
        for path in sorted((self.root / AI_FOLDER / "timing").glob(f"*/*_{book}{TIMING_SUFFIX}")):
            if self._v4(path.name[:10]):
                found.append(json.loads(path.read_text(encoding="utf-8")))
        return found

    def _v4(self, day: str) -> bool:
        return date.fromisoformat(day) >= self.live_from


def _minutes(start: str, end: str) -> float:
    return (datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds() / 60


def _spread(values: Sequence[float]) -> str:
    if not values:
        return "unknown"
    return f"p50 {nearest_rank(values, 0.50):.2f}, p95 {nearest_rank(values, 0.95):.2f}"
