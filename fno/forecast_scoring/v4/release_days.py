"""The release records as G8 reads them (story G10 completion, criterion 6): Drive's `v4/days/`, verified (see
`DriveRecords`), each parsed by the release record's own reader."""

from __future__ import annotations

import posixpath
from datetime import date

from ...v4_pack.release import parse_release
from .days import DayLabel, V4DaySource
from .drive_records import DriveRecords


class ReleasedDays(V4DaySource):
    def __init__(self, records: DriveRecords):
        self.records = records

    def labels(self) -> dict[date, DayLabel]:
        found = (parse_release(posixpath.splitext(posixpath.basename(path))[0], data)
                 for path, data in self.records.files().items())  # fmt: skip
        return {r.day: DayLabel(r.day, r.label, r.pack_sha256, r.observed_by) for r in found}
