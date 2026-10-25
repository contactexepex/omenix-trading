"""Recomputes the India VIX table from the archived month files and lists every difference (story A15).

Every month the table holds or the manifest lists is read back from the raw archive, its SHA-256 compared with the
manifest row, and its days compared with the table's rows cell by cell (values, source path and SHA-256), so a day
missing from either side is named. Read-only: nothing is changed.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from collections.abc import Callable, Mapping
from datetime import date

from ..storage.raw_store import RawFileStore
from .month_file import VixMonthReader
from .source import month_start
from .table import VALUE_FIELDS, value_cells

MISSING_ROW, DIFFERS = "no manifest row for the archived file", "SHA-256 differs from the manifest"


class VixTableVerifier:
    def __init__(
        self,
        archive: RawFileStore,
        path_for: Callable[[date], str],
        reader: VixMonthReader,
        manifest: Mapping[date, str],
    ):
        """`manifest`: month -> SHA-256 of its archived file, from the dataset's manifest."""
        self.archive, self.path_for, self.reader, self.manifest = archive, path_for, reader, manifest

    def problems(self, rows: list[dict[str, str]]) -> list[str]:
        """Every difference between the table and its archived month files ([] when they agree in full): a value or
        source that differs, a day the table holds that its file lacks, and a day of any archived month (in the
        manifest) that the table lacks, so a deleted month or a table cut short is named too."""
        days = [row["date"] for row in rows]
        order = [f"{d}: the table holds this day twice" for d in sorted({d for d in days if days.count(d) > 1})]
        order += [] if days == sorted(days) else ["the table's days are not in date order"]
        by_month: dict[date, list[dict[str, str]]] = defaultdict(list)
        for row in rows:
            by_month[month_start(date.fromisoformat(row["date"]))].append(row)
        months = sorted(set(by_month) | set(self.manifest))
        return order + [problem for month in months for problem in self._month(month, by_month.get(month, []))]

    def _month(self, month: date, held: list[dict[str, str]]) -> list[str]:
        path = self.path_for(month)
        data = self.archive.get(path)
        if data is None:
            return [f"{month:%Y-%m}: {path} is not in the archive"]
        sha256 = hashlib.sha256(data).hexdigest()
        want = self.manifest.get(month)
        problems = [] if want == sha256 else [f"{month:%Y-%m}: {MISSING_ROW if want is None else DIFFERS}"]
        try:
            days = self.reader.read(data, month)
        except ValueError as exc:
            return [*problems, f"{month:%Y-%m}: archived file fails the check: {exc}"]
        expected = {d.day.isoformat(): value_cells(d, path, sha256) for d in days}
        actual = {r["date"]: tuple(r[f] for f in VALUE_FIELDS) for r in held}
        for day in sorted(set(expected) | set(actual)):
            if expected.get(day) != actual.get(day):
                problems.append(f"{day}: table {actual.get(day)}, archived file {expected.get(day)}")
        return problems
