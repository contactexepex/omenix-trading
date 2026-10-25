"""What the post-mortem reads (story LR1), each behind a small interface so a test fakes it: the committed score
reports (G4, G8), the 3 pm capture markers and sidecars (A4, A4b) and A16's session count (the card deliveries are
T1's own `DeliveryLog`). Everything is a committed file; nothing here computes a score."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path


class ScoreReports(ABC):
    @abstractmethod
    def latest(self, on_or_before: date) -> tuple[str, dict] | None:
        """(the report's repository path, its document) of the latest report dated on or before the day."""


class ReportFolder(ScoreReports):
    """`<folder>/<YYYY-MM-DD>.json`, G4's and G8's layout."""

    def __init__(self, folder: Path, shown_as: str):
        self.folder, self.shown_as = Path(folder), shown_as

    def latest(self, on_or_before: date) -> tuple[str, dict] | None:
        found = sorted(p for p in self.folder.glob("*.json") if _dated(p.stem) and p.stem <= on_or_before.isoformat())
        if not found:
            return None
        return f"{self.shown_as}/{found[-1].name}", json.loads(found[-1].read_text(encoding="utf-8"))


def _dated(stem: str) -> bool:
    try:
        date.fromisoformat(stem)
    except ValueError:
        return False
    return True


@dataclass(frozen=True)
class CaptureState:
    complete: bool
    finished_at: datetime | None


class CaptureSource(ABC):
    @abstractmethod
    def capture(self, day: date) -> CaptureState | None:
        """The day's canonical 3 pm capture, or None when the day has no `.canonical` marker."""


class CaptureMarkers(CaptureSource):
    """`<folder>/<YYYY>/<MM>/nifty_<YYYYMMDD>.canonical` names the attempt; its sidecar is `<attempt>.meta.json`."""

    def __init__(self, folder: Path):
        self.folder = Path(folder)

    def capture(self, day: date) -> CaptureState | None:
        month = self.folder / f"{day:%Y}" / f"{day:%m}"
        marker = month / f"nifty_{day:%Y%m%d}.canonical"
        if not marker.is_file():
            return None
        sidecar = month / f"{marker.read_text(encoding='utf-8').strip()}.meta.json"
        if not sidecar.is_file():
            return CaptureState(False, None)
        meta = json.loads(sidecar.read_text(encoding="utf-8"))
        finished = meta.get("finished_at")
        return CaptureState(meta.get("complete") is True, datetime.fromisoformat(finished) if finished else None)


class SessionCount(ABC):
    @abstractmethod
    def count(self) -> int:
        """How many live A16 sessions are recorded."""


class IntradaySessions(SessionCount):
    def __init__(self, rows):
        self.rows = rows  # A16's `RvTable.rows` (live `rv/` rows only)

    def count(self) -> int:
        return len(self.rows())
