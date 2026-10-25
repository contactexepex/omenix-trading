"""v4 forecast records (story G7, layout agreed with G8): `research/forecasts/v4/<forecaster>/<question>.csv`, one row
per day; `day,value,status,label` first, G7's audit columns after. Rows are written once: the same row again changes
nothing, a different row for a day already written is refused."""

from __future__ import annotations

import csv
import io
import math
import re
from collections.abc import Iterable
from dataclasses import asdict, dataclass, fields
from datetime import date
from pathlib import Path

from ..forecast_v4.terms import POINT_QUESTIONS
from .baselines import OK

LIVE, BACKFILL = "live", "backfill_exploratory"
BASELINE, RULE = "baseline", "rule"
SLOT_RULES, SLOT_REPORTED = "rules", "reported"
VERSION = "1"
PACK_SHA256 = re.compile(r"(|[0-9a-f]{64})")  # empty, or the released pack's SHA-256


class InvalidRecord(ValueError):
    """A value outside its question's range: refused, never written."""


class RecordConflict(RuntimeError):
    """A day already has a different row; rows are never changed."""


@dataclass(frozen=True)
class Record:
    day: str
    value: str  # empty unless status is ok
    status: str
    label: str
    forecaster_version: str
    kind: str
    slot: str
    method_sha256: str
    inputs_sha256: str
    pack_sha256: str  # G10 part 2: the pack a pack-reading record used; empty for G7 and M1 (closes up to d-1 only)
    made_at: str  # empty for back-filled rows, so a re-run writes identical files

    def same_as(self, other: Record) -> bool:
        return {**asdict(self), "made_at": ""} == {**asdict(other), "made_at": ""}


COLUMNS = tuple(f.name for f in fields(Record))


def record(day: date, question: str, status: str, value: float | None, pack_sha256: str = "", version: str = VERSION,
           **audit: str) -> Record:  # fmt: skip
    """A validated row: a variance finite and > 0, a probability in [0, 1]; a value only when status is ok. A pack hash
    is empty or 64 lowercase hex characters (its form only: whether it is the released pack is G10's `fno/v4_pack`
    guard)."""
    if not PACK_SHA256.fullmatch(pack_sha256):
        raise InvalidRecord(f"{question} {day}: {pack_sha256!r} is not a pack SHA-256")
    if status == OK:
        bad = not math.isfinite(value) or (value <= 0 if question in POINT_QUESTIONS else not 0 <= value <= 1)
        if bad:
            raise InvalidRecord(f"{question} {day}: {value} is not a valid forecast")
        text = repr(float(value))
    else:
        text = ""
    return Record(day.isoformat(), text, status, forecaster_version=version, pack_sha256=pack_sha256, **audit)


def path(folder: Path, forecaster: str, question: str) -> Path:
    return folder / forecaster / f"{question}.csv"


def read(file: Path) -> dict[str, Record]:
    if not file.exists():
        return {}
    # a file written before G10 part 2 has no pack column: its rows read as empty, so it needs no rewrite
    return {r["day"]: Record(**{"pack_sha256": "", **r}) for r in csv.DictReader(io.StringIO(file.read_text()))}


def write(folder: Path, forecaster: str, question: str, rows: list[Record]) -> int:
    """Adds rows for new days; returns how many were added. Refuses (writing nothing) on any changed day."""
    file = path(folder, forecaster, question)
    kept = read(file)
    added = 0
    for row in rows:
        old = kept.get(row.day)
        if old is not None:
            if not old.same_as(row):
                raise RecordConflict(f"{forecaster}/{question} {row.day}: a different row is already written")
            continue
        kept[row.day] = row
        added += 1
    if added:
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(csv_text(kept.values()))
    return added


def csv_text(rows: Iterable[Record]) -> str:
    """The record file's text: the header, then one row per day in date order (the same rows give the same text)."""
    out = io.StringIO()
    writer = csv.DictWriter(out, COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(asdict(row) for row in sorted(rows, key=lambda row: row.day))
    return out.getvalue()


def first_live_day(folder: Path) -> date | None:
    """The earliest day with a live row in any v4 record file (the back-fill stops before it)."""
    days = [r.day for file in folder.glob("*/*.csv") for r in read(file).values() if r.label == LIVE]
    return date.fromisoformat(min(days)) if days else None
