"""When the source last wrote each day's file, from every record kept (story A8, judge 15): the archive's
Last-Modified table taken with the download, and the release recorder's log. The latest time per day wins: the bytes
held cannot be older than the newest write anyone recorded, so the latest is the safe bound."""

from __future__ import annotations

import csv
from datetime import date, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path

TABLE_FIELDS = ("date", "last_modified")  # last_modified as the source sent it (RFC 1123, e.g. "Fri, 09 Aug 2019 ...")


def read_last_modified_table(path: Path) -> dict[date, datetime]:
    rows = list(csv.DictReader(path.read_text(encoding="utf-8").splitlines()))
    if rows and tuple(rows[0]) != TABLE_FIELDS:
        raise ValueError(f"{path.name}: needs the columns {','.join(TABLE_FIELDS)}")
    return {date.fromisoformat(r["date"]): parsedate_to_datetime(r["last_modified"]) for r in rows}


def latest_writes(*records: dict[date, datetime]) -> dict[date, datetime]:
    latest: dict[date, datetime] = {}
    for record in records:
        for day, written in record.items():
            if day not in latest or written > latest[day]:
                latest[day] = written
    return latest
