"""The log of every archived copy of a cue's files (story A17): one CSV per cue in the repository, one row per copy,
append-only, written right after Drive accepted the copy. It is the cue's manifest: the copy's path, the exact
request, its SHA-256 and size, and when it was fetched."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

FIELDS = ("fetched_at", "path", "url", "form", "sha256", "size_bytes")


@dataclass(frozen=True)
class SnapshotRow:
    fetched_at: datetime
    path: str
    url: str
    form: tuple[tuple[str, str], ...]
    sha256: str
    size_bytes: int

    def cells(self) -> tuple:
        form = "&".join(f"{k}={v}" for k, v in self.form)
        return (self.fetched_at.isoformat(), self.path, self.url, form, self.sha256, self.size_bytes)


class SnapshotLog:
    def __init__(self, folder: Path):
        self.folder = Path(folder)

    def path_for(self, cue: str) -> Path:
        return self.folder / f"{cue}.csv"

    def append(self, cue: str, row: SnapshotRow) -> None:
        file = self.path_for(cue)
        new = not file.is_file()
        self.folder.mkdir(parents=True, exist_ok=True)
        with file.open("a", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, lineterminator="\n")
            if new:
                writer.writerow(FIELDS)
            writer.writerow(row.cells())

    def paths_by_sha256(self, cue: str) -> dict[str, str]:
        """SHA-256 -> the archived copy's path (the first copy with those bytes)."""
        file = self.path_for(cue)
        rows = csv.DictReader(file.read_text(encoding="utf-8").splitlines()) if file.is_file() else []
        found: dict[str, str] = {}
        for row in rows:
            found.setdefault(row["sha256"], row["path"])
        return found

    def fetched_by_sha256(self, cue: str) -> dict[str, datetime]:
        """SHA-256 -> when the first copy with those bytes was fetched."""
        file = self.path_for(cue)
        rows = csv.DictReader(file.read_text(encoding="utf-8").splitlines()) if file.is_file() else []
        found: dict[str, datetime] = {}
        for row in rows:
            found.setdefault(row["sha256"], datetime.fromisoformat(row["fetched_at"]))
        return found

    def fetched_on(self, cue: str, day: date) -> bool:
        """Whether a copy of this cue was fetched on that IST date (the once-a-day rule)."""
        return any(at.date() == day for at in self._all_fetch_times(cue))

    def _all_fetch_times(self, cue: str) -> list[datetime]:
        file = self.path_for(cue)
        rows = csv.DictReader(file.read_text(encoding="utf-8").splitlines()) if file.is_file() else []
        return [datetime.fromisoformat(row["fetched_at"]) for row in rows]

    def paths(self, cue: str) -> set[str]:
        """Every logged copy's path."""
        file = self.path_for(cue)
        rows = csv.DictReader(file.read_text(encoding="utf-8").splitlines()) if file.is_file() else []
        return {row["path"] for row in rows}

    def latest_fetch_on(self, cue: str, day: date) -> tuple[datetime, list[str]]:
        """The last fetch of that IST date: its time and every copy it saved (a fetch may save several files)."""
        file = self.path_for(cue)
        rows = list(csv.DictReader(file.read_text(encoding="utf-8").splitlines())) if file.is_file() else []
        times = [datetime.fromisoformat(r["fetched_at"]) for r in rows]
        last = max(t for t in times if t.date() == day)
        return last, [r["path"] for r, t in zip(rows, times, strict=True) if t == last]
