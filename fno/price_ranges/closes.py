"""Official index closes (part A4): NIFTY's committed `warmup_closes.csv` (O6), and BANKNIFTY's table derived from the
same archived NSE index-close files ("Nifty Bank"), kept in Drive (O9) as one content-named file per update. The one
outcome source G13b's scorer and FL1 both read (`Outcomes.close`)."""

from __future__ import annotations

import csv
import io
from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from datetime import date

from ..constants import NIFTY_SYMBOL, SESSION_REGULAR
from ..fo_bhavcopy import INDEX_NAMES, BadFile, read_index_closes
from ..forecast_v4_rules.series import DayValue, closes_rows, regular_closes
from ..research_data.calendar import SessionCalendar
from ..research_data.nifty_panel import DailyFiles

TABLE_HEADER = "date,close,index_file"
GAP = "{underlying} {day}: {why}"


class CloseSeries(ABC):
    @abstractmethod
    def closes(self, underlying: str) -> list[DayValue]:
        """The official close of every regular session on file, in date order."""


class Outcomes:
    """`close(underlying, day)`: the official close, or None while it is not on file (never filled)."""

    def __init__(self, series: CloseSeries):
        self.series, self.cache = series, {}

    def close(self, underlying: str, day: date) -> float | None:
        if underlying not in self.cache:
            self.cache[underlying] = {c.day: c.value for c in self.series.closes(underlying)}
        return self.cache[underlying].get(day)


class CommittedNiftyCloses(CloseSeries):
    """NIFTY 50 from `warmup_closes.csv` (built by O6 from the same index-close files)."""

    def __init__(self, read_text: Callable[[], str]):
        self.read_text = read_text

    def closes(self, underlying: str) -> list[DayValue]:
        if underlying != NIFTY_SYMBOL:
            raise KeyError(f"warmup_closes.csv holds NIFTY only, not {underlying}")
        return regular_closes(closes_rows(self.read_text()))


def table_rows(text: str) -> list[DayValue]:
    return [DayValue(date.fromisoformat(r["date"]), float(r["close"])) for r in csv.DictReader(io.StringIO(text))]


def table_text(rows: Sequence[tuple[date, float, str]]) -> str:
    return "\n".join([TABLE_HEADER, *(f"{d.isoformat()},{v!r},{name}" for d, v, name in rows)]) + "\n"


class IndexFileCloses:
    """Reads one index's official close from NSE's archived index-close files, regular sessions only."""

    def __init__(self, files: DailyFiles, calendar: SessionCalendar):
        self.files, self.calendar = files, calendar

    def regular_sessions(self, first: date, last: date) -> list[date]:
        return [d for d in self.calendar.sessions(first, last) if self.calendar.session_kind(d) == SESSION_REGULAR]

    def rows(self, underlying: str, first: date, last: date) -> tuple[list[tuple[date, float, str]], list[str]]:
        """`(day, close, file name)` for each regular session from first to last, and a gap line for each missing."""
        return self.rows_for(underlying, self.regular_sessions(first, last))

    def rows_for(self, underlying: str, days) -> tuple[list[tuple[date, float, str]], list[str]]:
        name, found, gaps = INDEX_NAMES[underlying], [], []
        for day in days:
            filename, data = self.files.get(day)
            if data is None:
                gaps.append(GAP.format(underlying=underlying, day=day, why="no index-close file"))
                continue
            try:
                closes = read_index_closes(data, filename)
            except BadFile as error:
                gaps.append(GAP.format(underlying=underlying, day=day, why=str(error)))
                continue
            if name in closes:
                found.append((day, closes[name], filename))
            else:
                gaps.append(GAP.format(underlying=underlying, day=day, why=f"no '{name}' row in {filename}"))
        return found, gaps


class TableCloses(CloseSeries):
    """An index's derived close table, read from the latest receipted table file (`latest_text`)."""

    def __init__(self, latest_text: Callable[[str], str | None], committed: CloseSeries):
        self.latest_text, self.committed = latest_text, committed

    def closes(self, underlying: str) -> list[DayValue]:
        if underlying == NIFTY_SYMBOL:
            return self.committed.closes(underlying)
        text = self.latest_text(underlying)
        return table_rows(text) if text else []
