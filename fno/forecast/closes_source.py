"""Official daily closes (NIFTY 50, India VIX) known before a live forecast day (protocol v2, change 4).

`DailyClosesSource` is the interface the live pack reads; `CommittedClosesFile` reads a committed closes table in the
warm-up closes format (`date, session, underlying, vix, index_file, index_sha256`, story A10). The daily index-close
download (story O6's GitHub Actions job) extends that history; this module never downloads anything itself. The hard
gate: every trading day before the forecast day must have both closes, else the history is stale and the methods that
read it record "no forecast" (`history_stale`).
"""

from __future__ import annotations

import csv
import hashlib
import io
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from pathlib import Path

CLOSES_COLUMNS = ("date", "nifty", "vix")


@dataclass(frozen=True)
class OfficialCloses:
    source: str  # the file or download the closes came from
    rows: dict[date, tuple[float, float]]  # day -> (NIFTY 50 close, India VIX close)

    def through(self, day: date) -> dict[date, tuple[float, float]]:
        """The closes of days before `day` only (the live pack never holds a close from `day` or later)."""
        return {d: v for d, v in self.rows.items() if d < day}

    def missing(self, trading_days: list[date]) -> list[date]:
        return [d for d in trading_days if d not in self.rows]

    @staticmethod
    def table_sha256(rows: dict[date, tuple[float, float]]) -> str:
        """The SHA-256 of the closes actually supplied, in a fixed text form (part of the pack's provenance)."""
        out = io.StringIO()
        writer = csv.writer(out, lineterminator="\n")
        writer.writerow(CLOSES_COLUMNS)
        writer.writerows((d.isoformat(), repr(n), repr(v)) for d, (n, v) in sorted(rows.items()))
        return hashlib.sha256(out.getvalue().encode("utf-8")).hexdigest()


class DailyClosesSource(ABC):
    @abstractmethod
    def closes(self) -> OfficialCloses:
        """Every official close the source holds."""


class CommittedClosesFile(DailyClosesSource):
    def __init__(self, path: Path):
        self.path = Path(path)

    def closes(self) -> OfficialCloses:
        if not self.path.exists():
            return OfficialCloses(self.path.name, {})
        reader = csv.DictReader(io.StringIO(self.path.read_text(encoding="utf-8")))
        rows = {
            date.fromisoformat(r["date"]): (float(r["underlying"]), float(r["vix"]))
            for r in reader
            if r["underlying"] and r["vix"]
        }
        return OfficialCloses(self.path.name, rows)
