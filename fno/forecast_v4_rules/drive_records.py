"""The v4 records kept in Drive (story G7b completion; CLAUDE.md and story O9: data files write-once in Drive, receipts
in GitHub): one JSON file per live row, `v4/records/live/<forecaster>/<question>/<YYYY>/<date>.json` (the row's record
fields and its day label, canonical JSON), and the exploratory back-fill CSVs `v4/records/backfill/<method12>/
<forecaster>/<question>_to_<last day>.csv`. The format's one owner: the capture writes it, G8 reads it."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date

from .records import Record

RECORDS_FOLDER = "v4/records"
LIVE_FOLDER, BACKFILL_FOLDER = f"{RECORDS_FOLDER}/live", f"{RECORDS_FOLDER}/backfill"
BACKFILL_TO, CSV, JSON = "_to_", ".csv", ".json"
METHOD_PREFIX = 12  # hex characters of the method hash in a back-fill path
DAY_LABEL = "day_label"  # protocol 1.6's label of the day (A), copied from the release record


def live_path(forecaster: str, question: str, day: date) -> str:
    return f"{LIVE_FOLDER}/{forecaster}/{question}/{day:%Y}/{day.isoformat()}{JSON}"


def backfill_path(method_sha256: str, forecaster: str, question: str, last_day: date) -> str:
    name = f"{question}{BACKFILL_TO}{last_day.isoformat()}{CSV}"
    return f"{BACKFILL_FOLDER}/{method_sha256[:METHOD_PREFIX]}/{forecaster}/{name}"


def live_bytes(row: Record, day_label: str) -> bytes:
    """Canonical JSON (sorted keys, UTF-8): the same row always gives the same bytes, so a rerun is a no-op."""
    return json.dumps({**asdict(row), DAY_LABEL: day_label}, sort_keys=True).encode("utf-8")


def read_live(data: bytes) -> tuple[Record, str]:
    fields = json.loads(data)
    label = fields.pop(DAY_LABEL)
    return Record(**fields), label


def backfill_name(file_name: str) -> tuple[str, date] | None:
    """`(question, last day)` from `<question>_to_<YYYY-MM-DD>.csv`; None for any other name."""
    stem, _, last = file_name.removesuffix(CSV).rpartition(BACKFILL_TO)
    if not (file_name.endswith(CSV) and stem):
        return None
    return stem, date.fromisoformat(last)
