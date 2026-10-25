"""G8 reads the v4 records kept in Drive (story G7b completion, part e) beside the repository CSVs (`ForecastFiles`).
The format is G7's (`forecast_v4_rules/drive_records.py`). What is read is decided from the receipts, never from
whatever sits on disk, and only verified bytes are read (O9):

- every live row (one JSON per day under `live/<forecaster>/<question>/`), checked against its path: label `live`,
  its day the file's date, day label `A`;
- for each forecaster and question with a back-fill, the file of this tree's method hash with the latest last day,
  every row `backfill_exploratory` with that full hash. A pair whose back-fill exists only for other code stops the
  report (regenerate it), never a silent drop;
- a chosen file Drive does not return with its receipted bytes stops the report (G10's `DriveRecords`, the one seam);
- one row per forecaster, question and day across every source: a second row stops the report and names it.
"""

from __future__ import annotations

import csv
import io
from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import asdict
from datetime import date

from ...constants import V4_DAY_A
from ...forecast_v4_rules.drive_records import (
    BACKFILL_FOLDER,
    JSON,
    LIVE_FOLDER,
    METHOD_PREFIX,
    backfill_name,
    read_live,
)
from ...forecast_v4_rules.records import BACKFILL, LIVE, Record
from .inputs import ForecastValue, V4ForecastSource, forecast_value

LIVE_PARTS, BACKFILL_PARTS = 4, 3  # <forecaster>/<question>/<YYYY>/<date>.json; <method12>/<forecaster>/<file>.csv


class DuplicateDay(RuntimeError):
    """Two rows for one forecaster, question and day: the report stops and names them."""


class StaleBackfill(RuntimeError):
    """A back-fill exists only for other code (another method hash): regenerate it before any report."""


class BadRecord(ValueError):
    """A row that does not match its file: wrong label, day, day label or method hash."""


def chosen_paths(paths: Iterable[str], method_sha256: str) -> list[str]:
    """From the receipted record paths (relative to the data area): every live file, and per forecaster and question
    this hash's latest back-fill file."""
    live, latest, other_code = [], {}, set()
    for path in paths:
        if path.startswith(f"{LIVE_FOLDER}/"):
            if len(path.removeprefix(f"{LIVE_FOLDER}/").split("/")) != LIVE_PARTS or not path.endswith(JSON):
                raise BadRecord(f"{path}: not a v4 record path")
            live.append(path)
            continue
        parts = path.removeprefix(f"{BACKFILL_FOLDER}/").split("/")
        named = backfill_name(parts[-1]) if len(parts) == BACKFILL_PARTS else None
        if not path.startswith(f"{BACKFILL_FOLDER}/") or named is None:
            raise BadRecord(f"{path}: not a v4 record path")
        (method, forecaster, _), (question, last) = parts, named
        if method != method_sha256[:METHOD_PREFIX]:
            other_code.add((forecaster, question))
        elif (forecaster, question) not in latest or last > latest[(forecaster, question)][0]:
            latest[(forecaster, question)] = (last, path)
    stale = sorted(other_code - set(latest))
    if stale:
        raise StaleBackfill(
            f"back-fill only for other code (not {method_sha256[:METHOD_PREFIX]}): {stale}; regenerate it"
        )
    return sorted(live) + sorted(path for _, path in latest.values())


class DriveForecastRecords(V4ForecastSource):
    def __init__(self, files: Mapping[str, bytes], method_sha256: str):
        """`files`: the chosen paths' verified bytes (`chosen_paths`, then `wiring.build_drive_records`)."""
        self.rows: dict[tuple[str, str], dict[str, Record]] = defaultdict(dict)
        for path, data in files.items():
            for forecaster, question, row in _rows(path, data, method_sha256):
                _add(self.rows[(question, forecaster)], row, f"{forecaster}/{question}")

    def forecasters(self, question: str) -> list[str]:
        return sorted(f for q, f in self.rows if q == question)

    def values(self, question: str, forecaster: str) -> dict[date, ForecastValue]:
        rows = self.rows.get((question, forecaster), {})
        return {date.fromisoformat(day): forecast_value(asdict(row)) for day, row in rows.items()}


class CombinedForecasts(V4ForecastSource):
    """Every source's forecasters and rows; a day held by two sources stops the report."""

    def __init__(self, sources: list[V4ForecastSource]):
        self.sources = sources

    def forecasters(self, question: str) -> list[str]:
        return sorted({f for source in self.sources for f in source.forecasters(question)})

    def values(self, question: str, forecaster: str) -> dict[date, ForecastValue]:
        found: dict[date, ForecastValue] = {}
        for source in self.sources:
            for day, value in source.values(question, forecaster).items():
                if day in found:
                    raise DuplicateDay(f"{forecaster}/{question} {day}: two sources hold a row for this day")
                found[day] = value
        return found


def _rows(path: str, data: bytes, method_sha256: str):
    if path.startswith(f"{LIVE_FOLDER}/"):
        forecaster, question, _, name = path.removeprefix(f"{LIVE_FOLDER}/").split("/")
        row, day_label = read_live(data)
        if (row.label, row.day, day_label) != (LIVE, name.removesuffix(JSON), V4_DAY_A):
            raise BadRecord(f"{path}: label {row.label}, day {row.day}, day label {day_label}")
        return [(forecaster, question, row)]
    _, forecaster, name = path.removeprefix(f"{BACKFILL_FOLDER}/").split("/")
    question, _ = backfill_name(name)
    rows = [Record(**raw) for raw in csv.DictReader(io.StringIO(data.decode("utf-8")))]
    for row in rows:
        if (row.label, row.method_sha256) != (BACKFILL, method_sha256):
            raise BadRecord(f"{path}: {row.day} has label {row.label} and method {row.method_sha256[:12]}")
    return [(forecaster, question, row) for row in rows]


def _add(rows: dict[str, Record], row: Record, where: str) -> None:
    if row.day in rows:
        raise DuplicateDay(f"{where} {row.day}: a second row for this day")
    rows[row.day] = row
