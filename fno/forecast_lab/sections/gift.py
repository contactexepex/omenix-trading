"""GIFT Nifty for the 08:50 morning edition (story FL1-1d-2; owner e70525ee, "(c) Both"): A22b's own write-once file,
pushed with its receipt about 08:41 (by 08:46 at the latest), read verified through O9's Drive cache. Shown only when
A22's status for it is ok or late (the only rows with a level), as context: its gap to the previous session's
official NIFTY close, never a cause. Missing at 08:50 (no receipt yet, a damaged copy, or a failed read), the edition
names it itself, so O8 needs no 08:50 row (judge 445). The evening does not show it: it is a pre-open cue."""

from __future__ import annotations

import csv
import io
from collections.abc import Callable
from datetime import date

from ...preopen.day_row import early_file
from ...storage.data_wiring import DATA_AREA
from ..page.cues import AVAILABLE, CONTEXT, NOT_AVAILABLE, Cue, Section, SectionView, missing

NAME = "GIFT Nifty"
SHOWN = ("ok", "late")
NOT_YET = "GIFT Nifty: A22's file for {day} is not out yet (or not verified)"
NO_LEVEL = "GIFT Nifty: A22 recorded no level today ({status}: {detail})"
EVENING = "GIFT Nifty is a pre-open cue: the morning edition only"


class GiftSection(Section):
    name = NAME

    def __init__(self, cache, previous_close: Callable[[date], float | None]):
        """`cache`: O9's verified `DriveCache`; `previous_close(day)`: the previous session's official NIFTY close."""
        self.cache, self.previous_close = cache, previous_close

    def _row(self, day: date) -> dict | None:
        path = f"{DATA_AREA}/{early_file('gift', day)}"
        report = self.cache.sync(path)
        local = self.cache.local(path)
        if report.problems or not local.is_file():
            return None
        rows = list(csv.DictReader(io.StringIO(local.read_text(encoding="utf-8"))))
        return rows[0] if rows else None

    def read(self, day: date, edition: str) -> SectionView:
        if edition != "morning":
            return SectionView(self.name, NOT_AVAILABLE, why=EVENING)
        row = self._row(day)
        if row is None:
            return missing(self.name, edition, NOT_YET.format(day=day))
        if row.get("gift_status") not in SHOWN or not row.get("gift_level"):
            return missing(self.name, edition, NO_LEVEL.format(status=row.get("gift_status"),
                                                               detail=row.get("gift_detail", "")))  # fmt: skip
        level, close = float(row["gift_level"]), self.previous_close(day)
        change = round((level / close - 1) * 100, 3) if close else None
        cue = Cue(self.name, level, change, "%", day, CONTEXT, text=None)
        return SectionView(self.name, AVAILABLE, day, (cue,))
