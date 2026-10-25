"""A4h's close read as the evening's `TodayCloses` (story FL1-1d; A4h merged 22 Oct): the day's record
(`closes/<yyyy>/<mm>/<day>.json`, else the 16:00 recheck), read verified through O9's Drive cache. A value is used only
when NSE stamped the list that day at or after 15:30, and only for an index whose list value is its official close
(NIFTY 50 and NIFTY BANK; never INDIA VIX). It stays labelled provisional until the next morning confirms it."""

from __future__ import annotations

import json
from datetime import date, datetime

from ..close_read.constants import DATA_AREA, STAMP_FORMAT, STAMP_FROM
from ..close_read.records import recheck_path, record_path
from .ranges import TodayCloses

LISTED = {"NIFTY": "NIFTY 50", "BANKNIFTY": "NIFTY BANK"}
LEVELS = ("open", "high", "low")  # A4h's record holds `open` from 22 Oct; high and low asked of A4h (FL1-1f)
NOT_READ = "A4h has no close read of {day} stamped after 15:30 (its 15:40 read, its 16:00 recheck)"
UNREAD = "A4h's close of {day} was not read ({problems})"


class A4hTodayCloses(TodayCloses):
    def __init__(self, cache):
        """`cache`: O9's verified `DriveCache`; a sync of one file's path brings that file, and a sync that brings
        nothing is a problem (O9, 23 Oct): each problem is kept for `why_missing`, never dropped."""
        self.cache, self.problems = cache, {}

    def _document(self, day: date) -> dict | None:
        problems = []
        for path in (record_path(day), recheck_path(day)):
            drive_path = f"{DATA_AREA}/{path}"
            report, local = self.cache.sync(drive_path), self.cache.local(drive_path)
            if report.problems or not local.is_file():  # an older copy on disk is never used past a problem
                problems += report.problems or [f"{drive_path}: not on disk after its sync"]
                continue
            self.problems.pop(day, None)
            return json.loads(local.read_text(encoding="utf-8"))
        self.problems[day] = problems
        return None

    @staticmethod
    def _stamped(document: dict, day: date) -> bool:
        try:
            stamp = datetime.strptime(document.get("nse_stamp") or "", STAMP_FORMAT)
        except ValueError:
            return False
        return stamp.date() == day and stamp.time() >= STAMP_FROM

    def _index(self, underlying: str, day: date) -> dict:
        """The index's row of a record stamped after 15:30 whose list value is its official close, else {}."""
        document = self._document(day)
        if document is None or not self._stamped(document, day):
            return {}
        index = (document.get("indices") or {}).get(LISTED.get(underlying, ""), {})
        return {} if index.get("official_close") is False else index

    def close(self, underlying: str, day: date) -> float | None:
        last = self._index(underlying, day).get("last")
        return float(last) if last is not None else None

    def levels(self, underlying: str, day: date) -> dict[str, float]:
        index = self._index(underlying, day)
        return {name: float(index[name]) for name in LEVELS if index.get(name) is not None}

    def why_missing(self, day: date) -> str:
        problems = self.problems.get(day)
        return UNREAD.format(day=day, problems="; ".join(problems)) if problems else NOT_READ.format(day=day)
