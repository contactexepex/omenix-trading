"""What the Record holds as provenance (NP11), read only: the union of a day's files (the day file and its numbered
supplements). Used by the writer (to add only what is missing), by the staging cleanup proof and by the recall
report."""

from __future__ import annotations

import re
from datetime import date

from fno.ingestion.news.provenance import file
from fno.ingestion.news.provenance.model import FOLDER, Pair, Pairs, path_of
from fno.ingestion.storage.raw_store import RawFileStore

NAME = re.compile(r"\A(\d{4}-\d{2}-\d{2})(?:-(\d+))?\.json\Z")


class ProvenanceUnreadable(Exception):
    """A provenance file of the day is damaged: nothing is written for that day, nothing is trusted from it."""


class ProvenanceIndex:
    def __init__(self, record: RawFileStore):
        """`record`: the Record area, read only (this class has no way to write)."""
        self.record = record
        self._days: dict[date, Pairs] = {}
        self._numbers: dict[date, int] = {}

    def pairs(self, day: date) -> Pairs:
        if day not in self._days:
            self._load(day)
        return self._days[day]

    def next_number(self, day: date) -> int:
        """0 for the first file of a day, else the number after the highest supplement."""
        self.pairs(day)
        return self._numbers[day]

    def feeds_of(self, day: date, key: str) -> frozenset[str]:
        return frozenset(feed for feed, _ in self.pairs(day).get(key, ()))

    def forget(self, day: date) -> None:
        """After a write: the next read of the day lists the folder again."""
        self._days.pop(day, None)
        self._numbers.pop(day, None)

    def _load(self, day: date) -> None:
        numbers = sorted(n for n in self._file_numbers(day))
        merged: dict[str, set[Pair]] = {}
        for number in numbers:
            data = self.record.get(path_of(day, number))
            try:
                found = file.parse(data) if data is not None else None
            except ValueError:
                found = None
            if found is None:
                raise ProvenanceUnreadable
            for key, items in found.items():
                merged.setdefault(key, set()).update(items)
        self._days[day] = {key: frozenset(items) for key, items in merged.items()}
        self._numbers[day] = (numbers[-1] + 1) if numbers else 0

    def _file_numbers(self, day: date) -> list[int]:
        stem = f"{day:%Y-%m-%d}"
        found = []
        for name in self.record.checksums(FOLDER):
            match = NAME.match(name)
            if match and match.group(1) == stem:
                found.append(int(match.group(2) or 0))
        return found
