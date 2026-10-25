"""NSE's official values for a day, from the index-close file: the copy archived in Drive (the version first archived,
which G13b scores), as every reader of these files gets it (`fno/storage/wiring.py` `build_stored_index_close_files`:
the stores only, never NSE and never a Drive write; a file not yet archived reads as missing). Each index has its
open, high, low and close (A4h-2). Behind an interface so a test or another archive swaps in one class."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from ..fo_bhavcopy import read_index_values
from ..research_data.nifty_panel import DailyFiles

OfficialValues = dict[str, dict[str, float | None]]  # official index name -> {"open", "high", "low", "close"}


class OfficialCloses(ABC):
    @abstractmethod
    def values(self, day: date) -> tuple[str, OfficialValues] | None:
        """The file's name and its values by official index name; None while no file exists yet. A damaged file
        raises `BadFile`."""


class ArchivedIndexCloses(OfficialCloses):
    def __init__(self, files: DailyFiles):
        self.files = files

    def values(self, day: date) -> tuple[str, OfficialValues] | None:
        filename, data = self.files.get(day)
        if data is None:
            return None
        return filename, read_index_values(data, filename)
