"""The daily index-close job (story O6, for G3's live forecasts): after NSE's evening file, the NIFTY 50 and India VIX
closes of every session since the warm-up file's last day are appended to it, read from the files archived in Drive
(the version first archived, so a row is what was known then; later NSE versions stay in Drive's revisions area).
It stops at the first session without its file or either close, keeps what came before it, and posts one line."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, timedelta
from pathlib import Path

from ..alerts.sender import AlertSender
from ..research_data.calendar import SessionCalendar
from ..research_data.nifty_panel import DailyFiles, PanelBuildError
from ..research_data.panel_store import WARMUP_FILE
from ..research_data.warmup_closes import append_warmup_rows, build_warmup_rows, last_warmup_day

ADDED = "index closes: {added} sessions added to {file} ({first} to {last})"
NOTHING_NEW = "index closes: nothing new after {last}"
STOPPED = (
    "Omenix F&O daily index closes: stopped at {day}: {problem}; {added} earlier sessions added. The next run retries"
)


class IndexCloseAppender:
    def __init__(
        self,
        index_files: DailyFiles,
        calendar: SessionCalendar,
        folder: Path,
        alerts: AlertSender,
        log: Callable[[str], None] = print,
    ):
        self.index_files, self.calendar, self.folder = index_files, calendar, Path(folder)
        self.alerts, self.log = alerts, log

    def run(self, today: date) -> int:
        last = last_warmup_day(self.folder)
        rows, stop = [], None
        for day in self.calendar.sessions(last + timedelta(days=1), today):
            try:
                rows += build_warmup_rows(self.index_files, self.calendar, day, day)
            except PanelBuildError as error:
                stop = (day, "; ".join(error.problems))
                break
        added = append_warmup_rows(self.folder, rows)
        if added:
            self.log(ADDED.format(added=added, file=WARMUP_FILE, first=rows[0][0], last=rows[-1][0]))
        else:
            self.log(NOTHING_NEW.format(last=last))
        if stop is None:
            return 0
        line = STOPPED.format(day=stop[0], problem=stop[1], added=added)
        self.log(line)
        self.log(self.alerts.send(line))
        return 1
