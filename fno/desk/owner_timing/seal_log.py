"""The committed seals of the availability file (story E8 rule 8): `research/desk/availability_seals.csv`, one row
per sealed version (`sealed_at,lines,sha256`). A seal counts for an order at T only once the commit that added its row
is on `main` before T, read from git's commit time, so a row written but never committed can never count. A shallow
clone cuts history at its boundary commit and dates every older seal to that commit, so an away day sealed weeks ago
would read as sealed too late and the entry would fill: the log refuses to answer there (judge 203, sf 1)."""

from __future__ import annotations

import csv
import io
import subprocess
from datetime import datetime
from pathlib import Path

from .availability import AvailabilityRefused, Seal, SealLog

FIELDS = ("sealed_at", "lines", "sha256")
PUBLISHED_REF = "origin/main"  # a seal counts once pushed: a local commit that never reached main never counts
SHALLOW = "the checkout is a shallow clone, so seal commit times are wrong: run git fetch --unshallow origin main"


class GitSealLog(SealLog):
    def __init__(self, repository: Path, relative_path: str, ref: str = PUBLISHED_REF):
        self.repository, self.relative_path, self.ref = Path(repository), relative_path, ref

    @property
    def file(self) -> Path:
        return self.repository / self.relative_path

    def sealed_before(self, moment: datetime) -> Seal | None:
        self._require_full_history()
        committed = [seal for seal in self._seals() if (when := self._committed_at(seal)) and when < moment]
        return committed[-1] if committed else None

    def latest(self) -> Seal | None:
        seals = self._seals()
        return seals[-1] if seals else None

    def add(self, seal: Seal, sealed_at: datetime) -> None:
        new = not self.file.exists()
        self.file.parent.mkdir(parents=True, exist_ok=True)
        with self.file.open("a", newline="") as out:
            writer = csv.DictWriter(out, fieldnames=FIELDS, lineterminator="\n")
            if new:
                writer.writeheader()
            writer.writerow({"sealed_at": sealed_at.isoformat(), "lines": seal.lines, "sha256": seal.sha256})

    def _seals(self) -> list[Seal]:
        if not self.file.exists():
            return []
        rows = csv.DictReader(io.StringIO(self.file.read_text()))
        return [Seal(int(row["lines"]), row["sha256"]) for row in rows]

    def _require_full_history(self) -> None:
        if self._git("rev-parse", "--is-shallow-repository").strip() != "false":
            raise AvailabilityRefused(SHALLOW)

    def _committed_at(self, seal: Seal) -> datetime | None:
        """The commit time of the first published commit whose change added this seal's hash."""
        found = self._git(
            "log", self.ref, "--format=%cI", "--reverse", "-S", seal.sha256, "--", self.relative_path
        ).split()
        return datetime.fromisoformat(found[0]) if found else None

    def _git(self, *args: str) -> str:
        return subprocess.run(["git", *args], cwd=self.repository, capture_output=True, text=True, check=False).stdout
