"""G14's live records: `research/forecasts/v5/v1_candle/<forecaster>/v1_rv_next_session.csv`, one row per day, G7's
record (`fno/forecast_v4_rules/records.py`, imported, never edited) plus three columns: the input measure label, the
inputs' sources and the capture's platform (judge 508's glibc finding). Written once: the same row again changes
nothing; a different value, status or input for a day already written is refused. G7's writer is not reused because
its column list is G7's own and frozen with v4."""

from __future__ import annotations

import csv
import io
import platform
from dataclasses import asdict, dataclass, fields
from pathlib import Path

import numpy as np

from ..forecast_v4_rules.records import Record, RecordConflict

INPUT_MEASURE = "candle RV (15m bars) vs live quote RV"
AUDIT_ONLY = ("made_at", "platform")  # where and when a row was made: a rerun elsewhere is the same row


@dataclass(frozen=True)
class V5Record(Record):
    input_measure: str
    input_sources: str  # `candle:<n>;live:<m>` for a forecaster reading the intraday series, `closes` otherwise
    platform: str

    def same_as(self, other: Record) -> bool:
        blank = dict.fromkeys(AUDIT_ONLY, "")
        return {**asdict(self), **blank} == {**asdict(other), **blank}


COLUMNS = tuple(f.name for f in fields(V5Record))


def v5_record(g7: Record, input_sources: str, made_on: str) -> V5Record:
    return V5Record(**asdict(g7), input_measure=INPUT_MEASURE, input_sources=input_sources, platform=made_on)


def capture_platform() -> str:
    """Python, numpy and C library versions of the machine making the row."""
    libc = " ".join(part for part in platform.libc_ver() if part) or "unknown"
    return f"python {platform.python_version()}; numpy {np.__version__}; libc {libc}"


def path(folder: Path, forecaster: str, question: str) -> Path:
    return folder / forecaster / f"{question}.csv"


def read(file: Path) -> dict[str, V5Record]:
    if not file.exists():
        return {}
    return {r["day"]: V5Record(**r) for r in csv.DictReader(io.StringIO(file.read_text()))}


def write_day(folder: Path, question: str, rows: dict[str, V5Record]) -> int:
    """One day's row per forecaster, all or nothing: every file is checked before any is written; returns how many
    rows were added. A different row already written for the day refuses the whole day."""
    files = {name: path(folder, name, question) for name in rows}
    kept = {name: read(file) for name, file in files.items()}
    new = {}
    for name, row in rows.items():
        old = kept[name].get(row.day)
        if old is None:
            new[name] = row
        elif not old.same_as(row):
            raise RecordConflict(f"{name}/{question} {row.day}: a different row is already written")
    for name, row in new.items():
        files[name].parent.mkdir(parents=True, exist_ok=True)
        files[name].write_text(_csv_text([*kept[name].values(), row]))
    return len(new)


def _csv_text(rows) -> str:
    out = io.StringIO()
    writer = csv.DictWriter(out, COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(asdict(row) for row in sorted(rows, key=lambda row: row.day))
    return out.getvalue()
