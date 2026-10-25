"""Where the NIFTY panel (story A3) is kept: the `PanelSink` interface and its folder of yearly
`options_<year>.csv.gz` and `futures_<year>.csv.gz` files plus `manifest.json`.

Deterministic: rows arrive sorted; the column order is fixed; gzip is written with no file name and a zero timestamp;
the manifest is sorted JSON with no build time in it. So the same raw files give byte-identical outputs. Files are
written under temporary names and swapped in only when the whole build succeeded. A build never shrinks the panel: a
range that would leave out days the existing manifest covers is refused before anything is read.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .panel_rows import TABLE_COLUMNS

TABLE_FILE = "{table}_{year}.csv.gz"
TABLE_GLOB = "*_[0-9][0-9][0-9][0-9].csv.gz"
MANIFEST_FILE = "manifest.json"
WARMUP_FILE = "warmup_closes.csv"  # closes before the first session, for feature history (story A10)
WARMUP_FIELDS = ("date", "session", "underlying", "vix", "index_file", "index_sha256")
PART_SUFFIX = ".part"
GZIP_LEVEL = 9


class PanelRangeError(ValueError):
    """The build's range would drop days the existing panel holds."""


def file_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class PanelDay:
    day: date
    entry: dict  # the day's manifest entry: session kind, status, source files and their SHA-256, row counts
    rows: dict[str, list[tuple[str, ...]]]  # table -> rows in its column order, sorted


@dataclass(frozen=True)
class Panel:
    manifest: dict


class PanelSink(ABC):
    @abstractmethod
    def begin(self, start: date, end: date) -> None:
        """Raises PanelRangeError when a build of this range would drop days of the existing panel."""

    @abstractmethod
    def add(self, panel_day: PanelDay) -> None:
        """Takes the days in date order."""

    @abstractmethod
    def finish(self, header: dict) -> Panel:
        """Makes the build final; the manifest is `header` plus the days and the output files."""

    @abstractmethod
    def discard(self) -> None:
        """Drops everything added; the previous panel stays as it was."""


class YearlyGzTable:
    """One table's part files, one per year, opened as the days arrive."""

    def __init__(self, folder: Path, table: str):
        self.folder, self.table, self.parts = folder, table, []
        self._year: int | None = None
        self._raw = self._text = self._writer = None

    def write(self, year: int, rows: list[tuple[str, ...]]) -> None:
        if year != self._year:
            self._open(year)
        self._writer.writerows(rows)

    def _open(self, year: int) -> None:
        self.close()
        part = self.folder / (TABLE_FILE.format(table=self.table, year=year) + PART_SUFFIX)
        self.parts.append(part)
        self._raw = part.open("wb")
        gz = gzip.GzipFile(filename="", mode="wb", fileobj=self._raw, compresslevel=GZIP_LEVEL, mtime=0)
        self._text = io.TextIOWrapper(gz, encoding="utf-8", newline="")
        self._writer = csv.writer(self._text, lineterminator="\n")
        self._writer.writerow(TABLE_COLUMNS[self.table])
        self._year = year

    def close(self) -> None:
        if self._text is not None:
            self._text.close()  # closes the gzip stream, which writes its trailer
            self._raw.close()
        self._raw = self._text = self._writer = None


class CsvGzPanelFolder(PanelSink):
    def __init__(self, folder: Path):
        self.folder = folder
        self.days: dict[str, dict] = {}
        self.tables = {table: YearlyGzTable(folder, table) for table in TABLE_COLUMNS}

    def begin(self, start: date, end: date) -> None:
        manifest = self.folder / MANIFEST_FILE
        if not manifest.is_file():
            return
        old = json.loads(manifest.read_text(encoding="utf-8"))
        if start.isoformat() > old["start"] or end.isoformat() < old["end"]:
            raise PanelRangeError(
                f"the panel holds {old['start']} to {old['end']}; a build of {start} to {end} would drop days. "
                f"Build at least {old['start']} to {old['end']} (delete {MANIFEST_FILE} to start a smaller panel)"
            )

    def add(self, panel_day: PanelDay) -> None:
        self.days[panel_day.day.isoformat()] = panel_day.entry
        for table, rows in panel_day.rows.items():
            if rows:
                self.folder.mkdir(parents=True, exist_ok=True)
                self.tables[table].write(panel_day.day.year, rows)

    def _parts(self) -> list[Path]:
        return [part for table in self.tables.values() for part in table.parts]

    def finish(self, header: dict) -> Panel:
        files = {}
        for table in self.tables.values():
            table.close()
        for part in self._parts():
            data = part.read_bytes()
            text = gzip.decompress(data)  # its SHA-256 checks the content whatever zlib version compressed it
            name = part.name.removesuffix(PART_SUFFIX)
            files[name] = {"sha256": file_sha256(data), "csv_sha256": file_sha256(text), "rows": text.count(b"\n") - 1}
        manifest = {**header, "files": files, "days": self.days}
        self.folder.mkdir(parents=True, exist_ok=True)
        for old in self.folder.glob(TABLE_GLOB):
            if old.name not in files:
                old.unlink()  # a file this build did not write would not match its manifest
        for part in self._parts():
            part.replace(part.with_name(part.name.removesuffix(PART_SUFFIX)))
        (self.folder / MANIFEST_FILE).write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n", "utf-8")
        return Panel(manifest)

    def discard(self) -> None:
        for table in self.tables.values():
            table.close()
        for part in self._parts():
            part.unlink(missing_ok=True)
        self.days = {}
        self.tables = {table: YearlyGzTable(self.folder, table) for table in TABLE_COLUMNS}
