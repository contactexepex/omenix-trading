"""Index closes of every NSE session (story A10): the NIFTY 50 and India VIX close of each session from 2017 on, read
from NSE's index-close files, so features have their history before the first year a run reads (F2 needs the previous
250 India VIX closes, F1 the previous 21 NIFTY 50 closes): 2017-18 for 2019, and, since judge 28, any earlier year for
a later period (story B3's discovery reads 2023's closes here, never 2023's option file).

Index closes only, never an option or future row: the 2017-18 F&O files are never opened (no experiment may see a
2018 outcome). A session without its file or either close fails the whole build, naming the days; nothing is written.
The file is derived data, committed next to the panel (`warmup_closes.csv`); the raw files stay in Drive.
"""

from __future__ import annotations

import csv
import io
import tempfile
from datetime import date
from pathlib import Path

from ..constants import INDEX_INDIA_VIX, INDEX_NIFTY_50
from ..fo_bhavcopy import BadFile, read_index_closes
from .calendar import SessionCalendar
from .nifty_panel import DailyFiles, PanelBuildError
from .panel_store import WARMUP_FIELDS, WARMUP_FILE, file_sha256


def build_warmup_rows(index_files: DailyFiles, calendar: SessionCalendar, start: date, end: date) -> list[tuple]:
    """One row per session from start to end; PanelBuildError naming every session without both closes."""
    rows, problems = [], []
    for day in calendar.sessions(start, end):
        filename, data = index_files.get(day)
        if data is None:
            problems.append(f"{day}: no index-close file {filename}")
            continue
        try:
            closes = read_index_closes(data, filename)
        except BadFile as exc:
            problems.append(f"{day}: {exc}")
            continue
        missing = [name for name in (INDEX_NIFTY_50, INDEX_INDIA_VIX) if name not in closes]
        if missing:
            problems.append(f"{day}: {filename} has no close for {missing}")
            continue
        session = calendar.session_kind(day)
        nifty, vix = closes[INDEX_NIFTY_50], closes[INDEX_INDIA_VIX]
        rows.append((day.isoformat(), session, nifty, vix, filename, file_sha256(data)))
    if problems:
        raise PanelBuildError(problems)
    return rows


def write_warmup_closes(folder: Path, rows: list[tuple]) -> Path:
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(WARMUP_FIELDS)
    writer.writerows(rows)
    path = Path(folder) / WARMUP_FILE
    with tempfile.NamedTemporaryFile("w", dir=folder, delete=False, encoding="utf-8", suffix=".part") as temporary:
        temporary.write(out.getvalue())
    Path(temporary.name).replace(path)  # never a half-written file
    return path


class WarmupConflict(RuntimeError):
    """A day already in the warm-up file came back with other values: rows are never rewritten."""


def last_warmup_day(folder: Path) -> date | None:
    path = Path(folder) / WARMUP_FILE
    if not path.is_file():
        return None
    days = [r["date"] for r in csv.DictReader(path.read_text(encoding="utf-8").splitlines())]
    return date.fromisoformat(days[-1]) if days else None


def append_warmup_rows(folder: Path, rows: list[tuple]) -> int:
    """Adds sessions after the file's last day (story O6: the daily job), in order, never touching an existing row: a
    day already there with the same values is skipped, with other values raises WarmupConflict. Returns rows added."""
    path = Path(folder) / WARMUP_FILE
    existing = (
        {r[0]: r for r in csv.reader(path.read_text(encoding="utf-8").splitlines()[1:])} if path.is_file() else {}
    )
    new = []
    for row in rows:
        text = [str(value) for value in row]
        if row[0] in existing:
            if existing[row[0]] != text:
                raise WarmupConflict(
                    f"{row[0]} is already in {WARMUP_FILE} with other values; rows are never rewritten"
                )
            continue
        new.append(text)
    last = last_warmup_day(folder)
    if new and last is not None and date.fromisoformat(new[0][0]) <= last:
        raise WarmupConflict(f"{new[0][0]} is not after the file's last day {last}; rows are only appended")
    if new:
        with path.open("a", encoding="utf-8", newline="") as out:
            csv.writer(out, lineterminator="\n").writerows(new)
    return len(new)
