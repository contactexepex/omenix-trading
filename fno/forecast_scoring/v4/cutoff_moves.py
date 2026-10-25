"""The live "moved after cutoff" flag (story G10, protocol section 1.6), as A16's 15:30 run committed it in each
session's rv row (`moved_after_cutoff`: yes, no, or empty when the 14:30 or 15:15 level was not usable). G8 reads the
committed value: no Drive at report time, and every re-run of a report gives the same counts."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from ...forecast_v4.cutoff_move import MOVED, NOT_MOVED


class CutoffMoves(ABC):
    @abstractmethod
    def moved(self, day: date) -> bool | None:
        """Whether the day moved more than X from 14:30 to 15:15; None when it cannot be computed."""


class RecordedCutoffMoves(CutoffMoves):
    def __init__(self, rows: list[dict]):
        self.flags = {r["session"]: r.get("moved_after_cutoff") for r in rows}  # rows before G10 have no column

    def moved(self, day: date) -> bool | None:
        flag = self.flags.get(day.isoformat())
        return True if flag == MOVED else False if flag == NOT_MOVED else None
