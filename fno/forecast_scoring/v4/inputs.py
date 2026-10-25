"""What G8 reads (story G8): v4 forecasts per (question, forecaster, day) and each forecast day's outcome. Both are
interfaces, so the files behind them (G7's forecast CSVs, G7's `series.py` rules) are swapped in the composition root.
"""

from __future__ import annotations

import csv
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from pathlib import Path

OK = "ok"  # G7's status of a row that carries a value; any other status is "no forecast that day"
LIVE = "live"


@dataclass(frozen=True)
class ForecastValue:
    value: float | None  # None: the forecaster gave no value that day (missing, not eligible, not started)
    live: bool  # False: a back-fill row (exploratory)


@dataclass(frozen=True)
class Outcome:
    """A forecast day's outcome. Unresolved: value None and not void. `vix` and `log_return` belong to the outcome's
    first session (the regime inputs of `regime.window_regime`)."""

    value: float | bool | None
    void: bool = False
    vix: float | None = None
    log_return: float | None = None


class V4ForecastSource(ABC):
    @abstractmethod
    def forecasters(self, question: str) -> list[str]:
        """Every forecaster id with a file for this question, sorted."""

    @abstractmethod
    def values(self, question: str, forecaster: str) -> dict[date, ForecastValue]:
        """One entry per day the forecaster's file has a row for; empty when it has no file."""


class V4OutcomeSource(ABC):
    @abstractmethod
    def outcomes(self, question: str) -> dict[date, Outcome]:
        """One entry per forecast day the question can have; a day beyond the data is unresolved."""


class ForecastFiles(V4ForecastSource):
    """G7's layout (agreed 15 Oct 2026): `<folder>/<forecaster>/<question>.csv`, first columns `day,value,status,label`;
    G7's audit columns after them are not read."""

    def __init__(self, folder: Path):
        self.folder = Path(folder)

    def forecasters(self, question: str) -> list[str]:
        return sorted(p.parent.name for p in self.folder.glob(f"*/{question}.csv"))

    def values(self, question: str, forecaster: str) -> dict[date, ForecastValue]:
        path = self.folder / forecaster / f"{question}.csv"
        if not path.is_file():
            return {}
        with path.open(encoding="utf-8", newline="") as handle:
            return {date.fromisoformat(row["day"]): forecast_value(row) for row in csv.DictReader(handle)}


def forecast_value(row: dict) -> ForecastValue:
    """A record row (as a dict of its columns) as G8 reads it: a value only when its status is ok."""
    value = float(row["value"]) if row["status"] == OK else None
    return ForecastValue(value, row["label"] == LIVE)
