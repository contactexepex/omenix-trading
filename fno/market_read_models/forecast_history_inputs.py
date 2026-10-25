"""What the forecast history page publishes (story P2, contract 2.9): G4's committed daily score reports
(`research/forecasts/scores/<day>.json`), every one dated on or before the session, oldest first. Read only; a report
that cannot be parsed stops the build, named (never a page with a day quietly missing)."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path


class ScoreReportsReader:
    def __init__(self, folder: Path):
        self.folder = Path(folder)

    def on(self, day: date) -> list[dict]:
        files = sorted(self.folder.glob("*.json")) if self.folder.is_dir() else []
        reports = [json.loads(f.read_text(encoding="utf-8")) for f in files if date.fromisoformat(f.stem) <= day]
        return sorted(reports, key=lambda r: r["as_of"])
