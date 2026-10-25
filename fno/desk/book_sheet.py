"""A book's own evaluation of the day, built in the pack step and kept in its private pack under "evaluation" (story
E2e, for F5's Book 2 rule default and F6's Book 3 candidates): one port, so every book that needs one adds a class and
one line in `pack_wiring.py`, never a file of its own under `journal/`. A sheet sees the day's common pack. It reads
only its own book's folders and cutoff-time data: the common pack holds no per-contract quotes (E2b), so a sheet that
prices reads the canonical 3 pm snapshot the common pack names in its provenance (`a4_snapshot`), never a later one."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from datetime import date

from .common_pack import CommonPack


class BookSheet(ABC):
    @abstractmethod
    def sheet(self, book: str, day: date, common: CommonPack) -> Mapping:
        """The book's evaluation for `day`, JSON-ready. Raising refuses that book's private pack (named, alerted)."""
