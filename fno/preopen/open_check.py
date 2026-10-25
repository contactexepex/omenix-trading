"""The open check (story A22d, amendment 2): each earlier session's pre-open values against NSE's official open in
that session's index-close file (read from the stores only), one write-once check file per session in Drive, and the
label of a flat 09:15 value: `verified` only when the index's 5 most recent checked flat values all match. A mismatch
is a problem line with no value; the difference stays in the Drive check file."""

from __future__ import annotations

import csv
import io
from collections.abc import Callable
from datetime import date

from ..intraday.minute_check import beyond
from ..intraday.nse_range import read_nse_day
from ..research_data.calendar import CalendarError
from ..storage.data_store import DataStore
from ..storage.raw_store import RawFileConflict
from .answers import BASIS_FLAT
from .check_files import PreopenFiles
from .day_row import UNVERIFIED, VERIFIED, day_file
from .problems import Problem

CHECK_FILE = "preopen/check/{day:%Y}/{day:%m}/{day:%Y-%m-%d}.csv"
CHECK_COLUMNS = ("date", "index", "basis", "result", "difference")
OFFICIAL_ROWS = {"nifty": "NIFTY 50", "banknifty": "NIFTY BANK"}  # A22's index prefix -> its index-close row
LOOK_BACK, TRUST_AFTER = 10, 5  # sessions checked (a long weekend, a late archive); matches before `verified`
MATCH, MISMATCH, NO_OFFICIAL = "match", "mismatch", "no official value"  # only `match` counts toward the label
STEP = "open check"
CHECKED = "open check: {checked} checked, {waiting} waiting for NSE's file"
MISMATCH_MESSAGE = "{what} differs from NSE's official open on {day}"
FLAT_VALUE, OTHER_VALUE = "flat 09:15 candle", "pre-open value"
NO_OFFICIAL_MESSAGE = "no readable {row} row in NSE's index-close file of {day}"
NOT_CHECKED = "{day}: NSE's index-close file still not archived after {sessions} sessions; it leaves the look-back"
CHECK_ERRORS = (OSError, RuntimeError, ValueError, CalendarError)  # Drive, its settings, an unreadable file or row


def check_file(day: date) -> str:
    return CHECK_FILE.format(day=day)


class OpenCheck:
    def __init__(self, previous_session: Callable[[date], date], files: PreopenFiles,
                 official: Callable[[date], bytes | None], store: DataStore):  # fmt: skip
        """`files`: A22's receipted Drive files; `official`: a session's index-close file from the stores, None when
        not archived yet; `store`: where the check files are written once."""
        self.previous_session, self.files, self.official, self.store = previous_session, files, official, store

    def run(self, today: date) -> tuple[str, list[Problem]]:
        """Checks every session of the look-back with a day row and no check file yet: its summary line and problems."""
        checked, waiting, problems = 0, 0, []
        try:
            sessions = self._sessions(today)
        except CalendarError as error:
            return CHECKED.format(checked=0, waiting=0), [Problem(STEP, "failed", str(error))]
        for n, day in enumerate(sessions, start=1):
            try:
                if self.files.has(check_file(day)) or not self.files.has(day_file(day)):
                    continue
                outcome = self._check(day)
            except RawFileConflict:
                problems.append(Problem(STEP, "taken", f"{day}: check file already written by another run"))
                continue
            except CHECK_ERRORS as error:
                problems.append(Problem(STEP, "failed", f"{day}: {type(error).__name__}"))
                continue
            if outcome is None:
                waiting += 1
                if n == LOOK_BACK:  # its last morning in the look-back: never dropped silently
                    problems.append(Problem(STEP, "not checked", NOT_CHECKED.format(day=day, sessions=LOOK_BACK)))
            else:
                checked += outcome[0]
                problems += outcome[1]
        return CHECKED.format(checked=checked, waiting=waiting), problems

    def labels(self, today: date) -> dict[str, str]:
        """Each index's label for today's flat 09:15 value, from the check files already written."""
        recent: dict[str, list[str]] = {index: [] for index in OFFICIAL_ROWS}
        for day in self._sessions(today):  # newest first
            if self.files.has(check_file(day)):
                for row in _rows(self.files.read(check_file(day))):
                    if row["index"] in recent and row["basis"].startswith(BASIS_FLAT):
                        recent[row["index"]].append(row["result"])
        return {index: _label(results[:TRUST_AFTER]) for index, results in recent.items()}

    def _sessions(self, today: date) -> list[date]:
        days, day = [], today
        for _ in range(LOOK_BACK):
            day = self.previous_session(day)
            days.append(day)
        return days

    def _check(self, day: date) -> tuple[int, list[Problem]] | None:
        """(1, its mismatches) once written; None while NSE's file is not archived; (0, []) for a row with no value."""
        row = _rows(self.files.read(day_file(day)))[0]
        values = {index: (float(row[f"{index}_preopen"]), row.get(f"{index}_preopen_basis") or "")
                  for index in OFFICIAL_ROWS if row.get(f"{index}_preopen")}  # fmt: skip
        if not values:
            return 0, []
        official = self.official(day)
        if official is None:
            return None
        lines, problems = [], []
        for index, (value, basis) in values.items():
            try:
                official_open = read_nse_day(official, OFFICIAL_ROWS[index]).open
            except ValueError:  # one index's row missing never hides the other's result
                lines.append((day.isoformat(), index, basis, NO_OFFICIAL, ""))
                problems.append(Problem(f"{index} {STEP}", NO_OFFICIAL,
                                        NO_OFFICIAL_MESSAGE.format(row=OFFICIAL_ROWS[index], day=day)))  # fmt: skip
                continue
            difference = round(value - official_open, 2)
            result = MISMATCH if beyond(difference) else MATCH
            lines.append((day.isoformat(), index, basis, result, f"{difference:.2f}"))
            if result == MISMATCH:
                what = FLAT_VALUE if basis.startswith(BASIS_FLAT) else OTHER_VALUE
                problems.append(Problem(f"{index} {STEP}", MISMATCH, MISMATCH_MESSAGE.format(what=what, day=day)))
        self.store.put(check_file(day), _csv(lines))
        return 1, problems


def _label(results: list[str]) -> str:
    return VERIFIED if len(results) == TRUST_AFTER and all(r == MATCH for r in results) else UNVERIFIED


def _rows(data: bytes) -> list[dict[str, str]]:
    rows = list(csv.DictReader(io.StringIO(data.decode())))
    if not rows:
        raise ValueError("no row")
    return rows


def _csv(lines: list[tuple[str, ...]]) -> bytes:
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerows([CHECK_COLUMNS, *lines])
    return out.getvalue().encode()
