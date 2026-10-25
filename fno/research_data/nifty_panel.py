"""Every NIFTY option and NIFTY future on every NSE session since 2019, built from the raw daily files (story A3).

For each session in NSE's calendar the day's F&O file is read in the first format that covers the day (current UDiFF
before the old format, so 2024 days before 6 July use UDiFF), with that day's index-close file for the NIFTY 50 close
(`underlying`) and the India VIX close (`vix`). A session without a file, a NIFTY 50 close or an India VIX close fails
the build, naming the day, unless a sourced exception (research/data/calendar/exceptions.csv) explains it; such a day
is left out of the panel and listed in the manifest. Values are copied, never guessed: a price with more than two
decimals or a count that is not whole fails the build instead of being rounded. Raw files are only read.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import InvalidOperation

from ..constants import (
    INDEX_INDIA_VIX,
    INDEX_NIFTY_50,
    PANEL_DAY_FAILED,
    PANEL_DAY_NO_FILE,
    PANEL_DAY_NO_INDEX,
    PANEL_DAY_OK,
)
from ..fo_bhavcopy import BadFile, read_fo_file, read_index_closes
from .calendar import SessionCalendar
from .panel_rows import FUTURES, OPTIONS, TABLE_COLUMNS, nifty_rows
from .panel_store import Panel, PanelDay, PanelSink, file_sha256

NamedFile = tuple[str, bytes | None]  # (original file name, its bytes; None when no store or source has it)


class PanelBuildError(RuntimeError):
    """The panel is not research-ready: the listed days broke a rule. Nothing was written."""

    def __init__(self, problems: list[str]):
        super().__init__(f"{len(problems)} day(s) not research-ready:\n" + "\n".join(problems))
        self.problems = problems


@dataclass(frozen=True)
class DailyFiles:
    """One dataset of dated raw files: its name in the exceptions file, the days it covers and how to get a day's
    file (wired in fno/storage/wiring.py from a `RawFileLibrary`: stores first, then NSE; never writes to Drive)."""

    label: str  # source_format for F&O files ("udiff", "legacy"); "index-close" for index closes
    dataset: str  # archive folder name, as in exceptions.csv
    first_day: date | None
    last_day: date | None
    get: Callable[[date], NamedFile]

    def covers(self, day: date) -> bool:
        return (self.first_day is None or day >= self.first_day) and (self.last_day is None or day <= self.last_day)


@dataclass
class DayResult:
    entry: dict
    rows: dict[str, list[tuple[str, ...]]] = field(default_factory=dict)
    problem: str | None = None


class NiftyPanelBuilder:
    def __init__(
        self,
        fo_files: Sequence[DailyFiles],
        index_files: DailyFiles,
        calendar: SessionCalendar,
        exceptions: dict[tuple[str, date], str],
    ):
        """`fo_files` in order of precedence: the first that covers a day and has its file is used."""
        self.fo_files, self.index_files, self.calendar, self.exceptions = fo_files, index_files, calendar, exceptions

    def days(self, start: date, end: date) -> Iterator[PanelDay]:
        problems = []
        for day in self.calendar.sessions(start, end):
            result = self._day(day)
            if result.problem:
                result.entry.update(status=PANEL_DAY_FAILED, problem=result.problem)
                problems.append(f"{day}: {result.problem}")
            yield PanelDay(day, result.entry, result.rows)
        if problems:
            raise PanelBuildError(problems)

    def _day(self, day: date) -> DayResult:
        entry = {"session": self.calendar.session_kind(day)}
        fo = self._fo_file(day)
        if fo is None:
            return self._missing(day, entry, [f.dataset for f in self.fo_files if f.covers(day)], PANEL_DAY_NO_FILE)
        files, (fo_name, fo_data) = fo
        entry.update(source_format=files.label, fo_file=fo_name, fo_sha256=file_sha256(fo_data))
        index_name, index_data = self.index_files.get(day)
        if index_data is None:
            return self._missing(day, entry, [self.index_files.dataset], PANEL_DAY_NO_INDEX)
        entry.update(index_file=index_name, index_sha256=file_sha256(index_data))
        try:
            closes = read_index_closes(index_data, index_name)
            missing = [name for name in (INDEX_NIFTY_50, INDEX_INDIA_VIX) if name not in closes]
            if missing:
                return DayResult(entry, problem=f"{index_name} has no closing value for {missing}")
            records = read_fo_file(fo_name, fo_data, closes)
            rows = nifty_rows(day, records, closes, files.label, entry["session"])
        except (BadFile, InvalidOperation) as exc:
            return DayResult(entry, problem=f"{type(exc).__name__}: {exc}")
        empty = [table for table in (OPTIONS, FUTURES) if not rows[table]]
        if empty:
            return DayResult(entry, problem=f"{fo_name} has no NIFTY {' or '.join(empty)} rows")
        entry.update(status=PANEL_DAY_OK, rows=len(rows[OPTIONS]), futures_rows=len(rows[FUTURES]))
        return DayResult(entry, rows)

    def _fo_file(self, day: date) -> tuple[DailyFiles, tuple[str, bytes]] | None:
        for files in self.fo_files:
            if files.covers(day):
                name, data = files.get(day)
                if data is not None:
                    return files, (name, data)
        return None

    def _missing(self, day: date, entry: dict, datasets: list[str], status: str) -> DayResult:
        """A session without a needed file is excused only by a sourced exception for each dataset that covers it."""
        reasons = [self.exceptions.get((dataset, day)) for dataset in datasets]
        if datasets and all(reasons):
            entry.update(status=status, exception="; ".join(reasons))
            return DayResult(entry)
        unexplained = [d for d, reason in zip(datasets, reasons, strict=True) if not reason] or [
            "(no dataset covers it)"
        ]
        return DayResult(entry, problem=f"{status}: no file and no sourced exception in {unexplained}")


def build_nifty_panel(
    fo_libraries: Sequence[DailyFiles],
    index_library: DailyFiles,
    start: date,
    end: date,
    *,
    calendar: SessionCalendar,
    exceptions: dict[tuple[str, date], str],
    sink: PanelSink,
) -> Panel:
    """Builds the panel into `sink`; on any gate failure the sink is discarded and PanelBuildError names the days."""
    if start > end:
        raise ValueError(f"empty range {start} to {end}: a build would replace the panel with nothing")
    sink.begin(start, end)  # refuses a range that would drop days of the existing panel
    builder = NiftyPanelBuilder(fo_libraries, index_library, calendar, exceptions)
    try:
        for panel_day in builder.days(start, end):
            sink.add(panel_day)
    except BaseException:
        sink.discard()
        raise
    header = {"start": start.isoformat(), "end": end.isoformat(), "calendar_sha256": calendar.calendar_sha256()}
    return sink.finish({**header, "columns": {table: list(columns) for table, columns in TABLE_COLUMNS.items()}})


def summary_lines(panel: Panel) -> list[str]:
    manifest = panel.manifest
    lines = [f"NIFTY panel {manifest['start']} to {manifest['end']}, calendar sha256 {manifest['calendar_sha256']}"]
    lines += [f"{name}: {f['rows']:,} rows, sha256 {f['sha256']}" for name, f in sorted(manifest["files"].items())]
    statuses: dict[str, int] = {}
    for entry in manifest["days"].values():
        statuses[entry["status"]] = statuses.get(entry["status"], 0) + 1
    lines.append("sessions: " + ", ".join(f"{count} {status}" for status, count in sorted(statuses.items())))
    lines += [
        f"left out {day}: {e['status']} ({e['exception']})" for day, e in manifest["days"].items() if "exception" in e
    ]
    return lines
