"""The NSE calendar's horizon (story O8b): once, when the calendar's last covered day is fewer than N days away, the
health message carries one line asking for the next year's holiday rows; without them every run fails from 1 January.

Once only: after the message is accepted by Slack, the marker file keeps the SHA-256 of the calendar it warned about. A
calendar with the same fingerprint never warns again; extending the calendar changes it, which re-arms the warning by
itself (the next year's horizon)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

HORIZON_MARKER = "research/ops/calendar_horizon_alerted.txt"
CALENDAR_PATH = "research/data/calendar/nse_sessions.csv"
# Look-ahead jobs (A14c's weekly stress run) stop earlier by their own rules; no other story's offset is copied here
WARNING = ("NSE calendar covers only to {last:%d %b %Y} ({days} days left): add every row of NSE's {year} holiday "
           f"circular to {CALENDAR_PATH} (source cited); look-ahead jobs such as A14c's stress run stop earlier, and "
           "every job that asks the calendar stops on 1 Jan {year}")  # fmt: skip


class CalendarHorizon:
    def __init__(self, last: date, sha256: str, marker: Path, days: int):
        self.last, self.sha256, self.marker, self.days = last, sha256, Path(marker), days

    def warning(self, run_day: date) -> str | None:
        left = (self.last - run_day).days
        if left >= self.days or self._warned():
            return None
        return WARNING.format(last=self.last, days=left, year=self.last.year + 1)

    def mark(self) -> None:
        self.marker.parent.mkdir(parents=True, exist_ok=True)
        self.marker.write_text(self.sha256 + "\n", encoding="utf-8")

    def _warned(self) -> bool:
        return self.marker.is_file() and self.marker.read_text(encoding="utf-8").strip() == self.sha256
