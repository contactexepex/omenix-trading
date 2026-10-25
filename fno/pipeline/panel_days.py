"""The daily NIFTY panel job (story A13; G1 protocol v3, responses 68 and 69): after NSE's evening F&O file, every
session after the panel's last day is built with A3's own builder (unchanged rules) from the **first archived version**
of its F&O and index-close files in Drive (A11's later versions are recorded, never used), and appended in place
(`PanelAppender`), never rewriting a day.

A run is all or nothing: it writes only under a frozen protocol (the injected freeze check runs first; a missing or
failing freeze record is an alerting failure, never a silent stop), only after the whole panel matches its manifest
(`verify`), and only if every pending session passes. Each session's inputs are
checked before it is built, with a named reason: `fo_file_missing`, `index_close_missing` (also when story O6 has not
appended that day's official close yet) or `index_close_differs` (O6's row came from another index-close version). The
first failure stops the run, appends nothing and posts one line; the next run (the morning retry) starts again from
the same day, so a missing day is never jumped over. Each appended day records its input versions (`provenance`).
"""

from __future__ import annotations

import csv
from collections.abc import Callable
from datetime import date, datetime, time, timedelta
from pathlib import Path

from ..alerts.sender import AlertSender
from ..constants import PANEL_FO_FILE_MISSING, PANEL_INDEX_CLOSE_DIFFERS, PANEL_INDEX_CLOSE_MISSING
from ..forecast.freeze import NotFrozen
from ..research_data.calendar import SessionCalendar
from ..research_data.nifty_panel import NiftyPanelBuilder, PanelBuildError
from ..research_data.panel_append import AppendRefused, PanelAppender
from ..research_data.panel_store import WARMUP_FILE, PanelDay

ADDED = "panel days: {added} sessions appended ({first} to {last})"
NOTHING_NEW = "panel days: nothing new after {last}"
STOPPED = "Omenix F&O daily NIFTY panel: nothing appended: {day}: {problem}. The next run retries from {day}"
REFUSED = "Omenix F&O daily NIFTY panel: nothing appended: {problem}"
FILES_BY = time(21, 0)  # IST: a session's F&O and index-close files are archived by then (the evening run is 21:41)
VersionLookup = Callable[[date, str], list[dict]]  # (day, dataset label) -> later A11 versions known now


def last_complete_day(now: datetime) -> date:
    """The last day whose session files can be expected: today from 21:00 IST, else yesterday (a morning retry or a
    manual run must not wait for today's session, which would stop the whole run)."""
    return now.date() if now.time() >= FILES_BY else now.date() - timedelta(days=1)


def official_index_files(folder: Path) -> dict[str, str]:
    """The index-close file SHA-256 behind each official close story O6 appended (`warmup_closes.csv`), by ISO date."""
    path = Path(folder) / WARMUP_FILE
    if not path.is_file():
        return {}
    return {r["date"]: r["index_sha256"] for r in csv.DictReader(path.read_text(encoding="utf-8").splitlines())}


def input_problem(builder: NiftyPanelBuilder, day: date) -> str | None:
    """The named reason a session cannot be built yet (None when its files are there or a sourced exception covers
    the gap, which A3's builder then records)."""
    fo = [f for f in builder.fo_files if f.covers(day)]
    if not any(f.get(day)[1] is not None for f in fo) and not _excused(builder, [f.dataset for f in fo], day):
        return f"{PANEL_FO_FILE_MISSING}: no F&O file archived in Drive"
    if builder.index_files.get(day)[1] is None and not _excused(builder, [builder.index_files.dataset], day):
        return f"{PANEL_INDEX_CLOSE_MISSING}: no index-close file archived in Drive"
    return None


def _excused(builder: NiftyPanelBuilder, datasets: list[str], day: date) -> bool:
    return bool(datasets) and all((dataset, day) in builder.exceptions for dataset in datasets)


def official_close_problem(panel_day: PanelDay, official: dict[str, str]) -> str | None:
    """The day's index-close file must be the one O6's official close came from (one day never has two closes)."""
    if "index_sha256" not in panel_day.entry:
        return None  # a sourced left-out day: no closes in the panel
    day = panel_day.day.isoformat()
    if day not in official:
        return f"{PANEL_INDEX_CLOSE_MISSING}: no {WARMUP_FILE} row yet (the daily index-close job appends it first)"
    if official[day] != panel_day.entry["index_sha256"]:
        return f"{PANEL_INDEX_CLOSE_DIFFERS}: {WARMUP_FILE} came from index-close version {official[day][:12]}"
    return None


class PanelDayJob:
    def __init__(
        self,
        builder: NiftyPanelBuilder,
        appender: PanelAppender,
        calendar: SessionCalendar,
        freeze_check: Callable[[], object],
        later_versions: VersionLookup,
        alerts: AlertSender,
        clock: Callable[[], datetime],
        log: Callable[[str], None] = print,
    ):
        self.builder, self.appender, self.calendar, self.freeze_check = builder, appender, calendar, freeze_check
        self.later_versions, self.alerts, self.clock, self.log = later_versions, alerts, clock, log

    def run(self, today: date) -> int:
        try:
            self.freeze_check()
        except NotFrozen as problem:  # not yet frozen too: a scheduled job never stops silently (judge 64 addendum 2)
            return self._fail(REFUSED.format(problem=f"protocol freeze check failed: {problem}"))
        try:
            self.appender.verify()
            return self._append(today)
        except AppendRefused as problem:
            return self._fail(REFUSED.format(problem=problem))

    def _append(self, today: date) -> int:
        started, last = self.clock(), self.appender.last_day()
        official, days = official_index_files(self.appender.folder), []
        for day in self.calendar.sessions(last + timedelta(days=1), today):
            panel_day, problem = self._built(day, official)
            if problem:
                return self._fail(STOPPED.format(day=day, problem=problem))
            days.append(PanelDay(day, {**panel_day.entry, **self._provenance(day, started)}, panel_day.rows))
        added = self.appender.append(days, {"calendar_sha256": self.calendar.calendar_sha256()})
        if added:
            self.log(ADDED.format(added=added, first=days[0].day, last=days[-1].day))
        else:
            self.log(NOTHING_NEW.format(last=last))
        return 0

    def _built(self, day: date, official: dict[str, str]) -> tuple[PanelDay | None, str | None]:
        problem = input_problem(self.builder, day)
        if problem:
            return None, problem
        try:
            (panel_day,) = list(self.builder.days(day, day))
        except PanelBuildError as error:
            return None, "; ".join(error.problems)
        return panel_day, official_close_problem(panel_day, official)

    def _provenance(self, day: date, started: datetime) -> dict:
        """Which version of each input the day used, what A11 knew of later ones, and when (ChatGPT review 30)."""
        return {
            "inputs_version": "first archived (A11 original)",
            "inputs_read_at": started.isoformat(),  # the archived files existed in Drive by then (an upper bound)
            "appended_at": self.clock().isoformat(),
            "later_versions": {label: self.later_versions(day, label) for label in ("fo", "index-close")},
        }

    def _fail(self, line: str) -> int:
        self.log(line)
        self.log(self.alerts.send(line))
        return 1
