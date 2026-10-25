"""Coverage of the AI books' forecasts (story G5 criterion 3, for G4's report): per book, the session days with at
least one counted probability out of the days that have a v2 pack (the days Book 1 forecast too). A day without an AI
record counts as missing, never as zero skill."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from ..constants import AI_BOOKS
from ..forecast.record_files import read_records_v2
from .paths import LIVE_PACK_FOLDER, records_path

PACK_SUFFIX = "_pack.json"


def pack_days(root: Path) -> list[date]:
    folder = Path(root) / LIVE_PACK_FOLDER
    return sorted(date.fromisoformat(p.name[: -len(PACK_SUFFIX)]) for p in folder.glob(f"*/*{PACK_SUFFIX}"))


def coverage(root: Path) -> dict[str, tuple[int, int]]:
    """book -> (days with a counted forecast, days with a v2 pack)."""
    days, result = pack_days(root), {}
    for book in AI_BOOKS:
        covered = 0
        for day in days:
            path = Path(root) / records_path(day, book)
            records = read_records_v2(path.read_text(encoding="utf-8")) if path.is_file() else []
            covered += any(r.record.probability is not None for r in records)
        result[book] = (covered, len(days))
    return result


def coverage_lines(root: Path) -> list[str]:
    return [f"{book}: {covered} of {total} pack days with a counted forecast"
            for book, (covered, total) in coverage(root).items()]  # fmt: skip
