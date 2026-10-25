"""The paired decision rows (story F9a): one per day a book committed its real decision, naming the unit ablated that
day, the units whose cards the real decision consulted, the real and the shadow decision, the hashes of the packs each
used and the execution snapshot each was valued on. F9b writes them; F9a only reads them."""

from __future__ import annotations

import csv
import io
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from ..constants import JOURNAL_FOLDER

PAIRED_FILE = "role_value/paired.csv"
COLUMNS = ("day", "book", "version", "unit", "consulted_units", "real_decision_id", "shadow_decision_id",
           "real_packs_sha256", "shadow_packs_sha256", "real_snapshot_id", "shadow_snapshot_id", "status")  # fmt: skip
SCORED, SHADOW_UNAVAILABLE, UNSCORED = "scored", "shadow_unavailable", "unscored"
STATUSES = (SCORED, SHADOW_UNAVAILABLE, UNSCORED)
UNIT_SEPARATOR = ";"


@dataclass(frozen=True)
class PairedRow:
    day: date
    book: str
    version: str
    unit: str
    consulted_units: tuple[str, ...]
    real_decision_id: str
    shadow_decision_id: str
    real_packs_sha256: str
    shadow_packs_sha256: str
    real_snapshot_id: str
    shadow_snapshot_id: str
    status: str

    @property
    def consulted(self) -> bool:
        """The ablated unit's card was consulted by the real decision: the opportunity applies to it."""
        return self.unit in self.consulted_units


class PairedDecisionSource(ABC):
    @abstractmethod
    def rows(self, book: str) -> list[PairedRow]:
        """The book's rows in day order; ValueError on a damaged file."""


def parse_row(line: int, raw: dict) -> PairedRow:
    if None in raw or None in raw.values():
        raise ValueError(f"{PAIRED_FILE} line {line}: wrong number of fields")
    if raw["status"] not in STATUSES:
        raise ValueError(f"{PAIRED_FILE} line {line}: status must be one of {STATUSES}, not {raw['status']!r}")
    consulted = tuple(u for u in raw["consulted_units"].split(UNIT_SEPARATOR) if u)
    fields = {k: raw[k] for k in COLUMNS if k not in ("day", "consulted_units")}
    return PairedRow(day=date.fromisoformat(raw["day"]), consulted_units=consulted, **fields)


class PairedRowFile(PairedDecisionSource):
    def __init__(self, root: Path):
        self.root = Path(root)

    def path(self, book: str) -> Path:
        return self.root / JOURNAL_FOLDER / book / PAIRED_FILE

    def rows(self, book: str) -> list[PairedRow]:
        path = self.path(book)
        if not path.is_file():
            return []
        reader = csv.DictReader(io.StringIO(path.read_text(encoding="utf-8")))
        if tuple(reader.fieldnames or ()) != COLUMNS:
            raise ValueError(f"{PAIRED_FILE} columns must be {COLUMNS}")
        rows = [parse_row(line, raw) for line, raw in enumerate(reader, start=2)]
        return sorted(rows, key=lambda row: row.day)
