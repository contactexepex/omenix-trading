"""A4h's Drive paths and the JSON of each file: the day's record, the recheck, the confirmation and the overdue mark."""

from __future__ import annotations

import json
from datetime import date

from .answer import ListRead
from .constants import INDICES, ROOT


def day_folder(day: date) -> str:
    return f"{ROOT}/{day:%Y}/{day:%m}"


def record_path(day: date) -> str:
    return f"{day_folder(day)}/{day.isoformat()}.json"


def recheck_path(day: date) -> str:
    return f"{day_folder(day)}/{day.isoformat()}.recheck.json"


def confirm_path(day: date) -> str:
    return f"{day_folder(day)}/{day.isoformat()}.confirm.json"


def overdue_path(day: date) -> str:
    return f"{day_folder(day)}/{day.isoformat()}.overdue.json"


def raw_path(day: date, which: str) -> str:
    return f"{day_folder(day)}/{day.isoformat()}.{which}.raw.json"


def day_of(path: str) -> date | None:
    """The day of a record path (`closes/2026/10/2026-10-21.json`), None for any other file."""
    name = path.rsplit("/", 1)[-1]
    stem = name.removesuffix(".json")
    if stem == name or "." in stem:
        return None
    try:
        return date.fromisoformat(stem)
    except ValueError:
        return None


def encode(document: dict) -> bytes:
    return (json.dumps(document, indent=1, sort_keys=True) + "\n").encode()


def read_document(day: date, read_at: str, got: ListRead, which: str, raw: tuple[str, str]) -> dict:
    """The day's record: every index's `last`, `open`, day range and previous close from the list (A4h-2), provisional
    until confirmed; `problems` holds INDIA VIX's range findings (a checked index with one is never recorded)."""
    return {
        "day": day.isoformat(), "read": which, "read_at": read_at, "nse_stamp": got.stamp, "provisional": True,
        "source": "NSE /api/allIndices", "raw_path": raw[0], "raw_sha256": raw[1], "problems": got.problems,
        "indices": {n.listed: {**got.values[n.listed], "official_close": n.checked} for n in INDICES},
    }  # fmt: skip


def recheck_document(day: date, read_at: str, got: ListRead, against: tuple[dict, dict], raw: tuple[str, str]) -> dict:
    """`against`: `last`'s comparison per index (as A4h wrote it), then each other field's (A4h-2)."""
    return {"day": day.isoformat(), "read_at": read_at, "nse_stamp": got.stamp, "raw_path": raw[0],
            "raw_sha256": raw[1], "indices": got.values, "against_first": against[0],
            "fields_against_first": against[1], "problems": got.problems}  # fmt: skip
