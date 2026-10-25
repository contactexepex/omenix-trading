"""Where an append-only table's rows live (story A17; shared since O9b, which moved it here from `fno/global_cues/` for
the India VIX table too): an append-only log of CSV rows behind one interface.

- `CsvRowLog`: one CSV file in the repository, appended to (old bytes stay a prefix). For public-domain cues.
- `DrivePartsRowLog`: a folder in the owner's Drive holding one new CSV part per append, never rewritten (Drive's
  copies are write-once). Its rows are every part's rows in name order. For cues whose values must never enter this
  public repository (owner decision a927390, 15 Oct 2026: the S&P 500 and Nasdaq 100 closes; story A17d: FBIL's
  USD/INR rate).
"""

from __future__ import annotations

import csv
import io
from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from .raw_store import RawFileStore

PART_NAME = "{at:%Y%m%dT%H%M%S%f}.csv"  # sorts in append order


class TableFileBroken(RuntimeError):
    """A log that cannot be appended to without changing what it already holds."""


class RowLog(ABC):
    @abstractmethod
    def rows(self) -> list[dict[str, str]]:
        """Every row appended so far, in order."""

    @abstractmethod
    def check_appendable(self) -> None:
        """Raises TableFileBroken when an append would change existing rows (checked before any write)."""

    @abstractmethod
    def append(self, fields: tuple[str, ...], rows: list[tuple]) -> None:
        """Adds rows after the existing ones; nothing existing changes."""


def _csv_text(fields: tuple[str, ...] | None, rows: list[tuple]) -> str:
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    if fields:
        writer.writerow(fields)
    writer.writerows(rows)
    return out.getvalue()


class CsvRowLog(RowLog):
    def __init__(self, path: Path):
        self.path = Path(path)

    def rows(self) -> list[dict[str, str]]:
        return list(csv.DictReader(self.path.read_text(encoding="utf-8").splitlines())) if self.path.is_file() else []

    def check_appendable(self) -> None:
        if self.path.is_file() and self.path.stat().st_size and not self.path.read_bytes().endswith(b"\n"):
            raise TableFileBroken(f"{self.path.name} does not end with a new line: appending would change its last row")

    def append(self, fields: tuple[str, ...], rows: list[tuple]) -> None:
        if not rows:
            return
        new = not self.path.is_file() or self.path.stat().st_size == 0
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="") as f:
            f.write(_csv_text(fields if new else None, rows))


class DrivePartsRowLog(RowLog):
    def __init__(self, store: RawFileStore, folder: str, clock: Callable[[], datetime]):
        """`store` lists and reads the folder (`checksums`, `get`) and writes new parts (`put`, never overwriting)."""
        self.store, self.folder, self.clock = store, folder, clock
        self._rows: list[dict[str, str]] | None = None  # read once, then kept in step with this log's own appends

    def rows(self) -> list[dict[str, str]]:
        if self._rows is None:
            self._rows = self._read()
        return list(self._rows)

    def _read(self) -> list[dict[str, str]]:
        found = []
        for name in sorted(self.store.checksums(self.folder)):
            data = self.store.get(f"{self.folder}/{name}")
            if data is None:
                raise TableFileBroken(f"{self.folder}/{name} is listed but cannot be read")
            found += list(csv.DictReader(data.decode("utf-8").splitlines()))
        return found

    def check_appendable(self) -> None:
        """Every append is a new write-once part: nothing existing can change."""

    def append(self, fields: tuple[str, ...], rows: list[tuple]) -> None:
        if rows:
            name = PART_NAME.format(at=self.clock())
            text = _csv_text(fields, rows)
            self.store.put(f"{self.folder}/{name}", text.encode("utf-8"))
            if self._rows is not None:
                self._rows += list(csv.DictReader(text.splitlines()))


class DriveSnapshots:
    """A report rewritten every run, kept in Drive as one new write-once file per run: the newest file is current (a
    gap that later clears is gone from it; nothing older is changed)."""

    def __init__(self, store: RawFileStore, folder: str, clock: Callable[[], datetime]):
        self.store, self.folder, self.clock = store, folder, clock

    def write(self, fields: tuple[str, ...], rows: list[tuple]) -> None:
        name = PART_NAME.format(at=self.clock())
        self.store.put(f"{self.folder}/{name}", _csv_text(fields, rows).encode("utf-8"))

    def latest(self) -> list[dict[str, str]]:
        names = sorted(self.store.checksums(self.folder))
        if not names:
            return []
        data = self.store.get(f"{self.folder}/{names[-1]}") or b""
        return list(csv.DictReader(data.decode("utf-8").splitlines()))
