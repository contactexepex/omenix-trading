"""Writes an AI book's day (stories F1 and G5): five records in the frozen v2 schema and the audit file beside them.
Written once: the first collection stands, and a later one (a re-run, a reveal that came after the collection) only
says whether it would differ. The audit file holds the full reasoning for the judge and the owner; screens must not
show it (strategy internals stay private)."""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

from ..constants import FORECAST_QUESTIONS
from ..forecast.record_files import records_csv_v2
from ..forecast.schema import ForecastRecord
from ..forecast.schema_v2 import ForecastRecordV2
from ..models import IST
from .outcome import Outcome
from .paths import audit_path, records_path
from .versions import version_by_label

LIVE_MODE, CUTOFF_HOUR = "live_1500_proxy", 15
ALREADY = "already recorded"


class AiRecordWriter:
    def __init__(self, root: Path):
        self.root = Path(root)

    def write(self, day: date, pack_sha: str, pack: dict, outcome: Outcome, fired: dict, now: datetime) -> str:
        records = self._records(day, pack_sha, pack, outcome, now)
        texts = {records_path(day, outcome.book): records_csv_v2(records),
                 audit_path(day, outcome.book): audit_text(day, outcome, fired)}  # fmt: skip
        existing = {p: (self.root / p).read_text(encoding="utf-8") for p in texts if (self.root / p).is_file()}
        if existing:
            return ALREADY if existing == texts else f"{ALREADY}; this collection differs, the first stands"
        for path, text in texts.items():
            (self.root / path).parent.mkdir(parents=True, exist_ok=True)
            (self.root / path).write_text(text, encoding="utf-8")
        return "recorded"

    @staticmethod
    def receipt_line(day: date, outcome: Outcome) -> str:
        received = outcome.committed_at.isoformat() if outcome.committed_at else "none"
        return f"ai receipt: {day} {outcome.book} status {outcome.status} commitment_received_at {received}"

    @staticmethod
    def _records(day, pack_sha, pack, outcome: Outcome, now: datetime) -> list[ForecastRecordV2]:
        cutoff = datetime(day.year, day.month, day.day, CUTOFF_HOUR, tzinfo=IST)
        generated = outcome.committed_at or now
        iv30 = (pack.get("iv30") or {}).get("status") or "none"
        return [ForecastRecordV2(ForecastRecord(outcome.book, day, cutoff, q, outcome.probabilities[q], outcome.version,
                                                pack_sha), LIVE_MODE, iv30, generated)
                for q in FORECAST_QUESTIONS]  # fmt: skip


def audit_text(day: date, outcome: Outcome, fired: dict, v4: dict | None = None) -> str:
    """The audit file of one book-day: the full reasoning for the judge and the owner (both protocols; v4 adds the
    collection time its rows carry as `made_at` and the release record's pack SHA)."""
    audit = {
        "book": outcome.book, "day": day.isoformat(), "version": outcome.version, "status": outcome.status,
        "isolation": version_by_label(outcome.version).isolation, "notes": outcome.notes,
        "commitment_received_at": outcome.committed_at.isoformat() if outcome.committed_at else None,
        "reveal_received_at": outcome.revealed_at.isoformat() if outcome.revealed_at else None,
        "model_reported": outcome.model_reported, "model_check": outcome.model_check,
        "counted": outcome.probabilities, "problems": outcome.problems, "attempted": outcome.attempted,
        "fire": fired,
    } | (v4 or {})  # fmt: skip
    return json.dumps(audit, sort_keys=True, indent=1, ensure_ascii=False) + "\n"
