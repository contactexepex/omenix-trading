"""What the archive cannot hold and why (story A12): one row per company and filing type with a sourced reason, kept
in the repository next to the manifests, so a gap is listed and explained, never silently skipped.

Each run replaces the rows of the companies it checked and keeps the others.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Iterable
from pathlib import Path

from .filing import FilingGap

GAP_FIELDS = ("symbol", "kind", "reason")


class GapLog:
    def __init__(self, path: Path):
        self.path = Path(path)

    def read(self) -> list[FilingGap]:
        if not self.path.is_file():
            return []
        rows = csv.DictReader(self.path.read_text(encoding="utf-8").splitlines())
        return [FilingGap(r["symbol"], r["kind"], r["reason"]) for r in rows]

    def replace(self, checked: Iterable[str], gaps: Iterable[FilingGap]) -> None:
        """Keeps the rows of companies not checked in this run; the checked ones get exactly `gaps`."""
        checked = set(checked)
        rows = [g for g in self.read() if g.symbol not in checked] + list(gaps)
        out = io.StringIO()
        writer = csv.writer(out, lineterminator="\n")
        writer.writerow(GAP_FIELDS)
        writer.writerows(
            (g.symbol, g.kind, g.reason) for g in sorted(set(rows), key=lambda g: (g.symbol, g.kind, g.reason))
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(out.getvalue(), encoding="utf-8")
