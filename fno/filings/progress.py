"""The filings archive's progress record (story A12, owner 13 Oct 2026): one JSON file in Drive's `index` area, read
at the start of every run and rewritten as companies finish, so each run continues where the last one stopped. It
holds the owner's work queue, the companies each step has finished, and a short history of runs (counts only).

Queue: step 1, today's Nifty 500 over the last 3 years; step 2, the same companies as far back as NSE has filings.
After the last step, a daily run reads every company's lists for new filings and revisions.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from ..models import now_utc
from ..storage.index_store import IndexFileStore
from .librarian import FilingsReport

PROGRESS_PATH = "nse/equities/filings/progress.json"
RUNS_KEPT = 120  # about a month of runs at four a day
DAILY_LOOKBACK = timedelta(days=400)  # a daily run re-reads a year of lists: new filings and late revisions


@dataclass(frozen=True)
class Step:
    name: str
    since: date  # filings made public on or after this day
    day_lists_since: date  # first day of the all-company announcement and board-meeting lists


QUEUE = (
    Step("1 last 3 years", date(2023, 10, 1), date(2023, 10, 13)),
    Step("2 older years", date(2005, 1, 1), date(2005, 1, 1)),  # NSE's lists start in 2005; XBRL files in 2018
)


class ProgressRecord:
    def __init__(self, store: IndexFileStore):
        self.store = store
        data = store.get(PROGRESS_PATH)
        self.state = json.loads(data) if data else {"done": {}, "runs": []}

    def step(self) -> Step | None:
        """The first step of the queue not yet finished (None: the backfill is done; runs are daily)."""
        finished = self.state.get("finished_steps", [])
        return next((s for s in QUEUE if s.name not in finished), None)

    def remaining(self, step: Step | None, companies: list[str]) -> list[str]:
        """The step's companies not finished yet, in list order (a daily run takes them all)."""
        done = set(self.state["done"].get(step.name, [])) if step else set()
        return [c for c in companies if c not in done]

    def fetched(self) -> set[str]:
        """Every company some step has finished: its NSE lists were read in full at least once."""
        return {s for done in self.state["done"].values() for s in done}

    def since(self, step: Step | None, today: date) -> date:
        return step.since if step else today - DAILY_LOOKBACK

    def finish_companies(self, step: Step | None, symbols: list[str]) -> None:
        if step:
            done = self.state["done"].setdefault(step.name, [])
            done += [s for s in symbols if s not in done]

    def finish_step_if_done(self, step: Step | None, companies: list[str]) -> None:
        if step and not self.remaining(step, companies):
            self.state.setdefault("finished_steps", []).append(step.name)

    def last_daily_run(self) -> datetime | None:
        daily = [r["finished"] for r in self.state["runs"] if r["step"] == "daily" and r["result"] == "complete"]
        return datetime.fromisoformat(max(daily)) if daily else None

    def record_run(self, step: Step | None, started: datetime, finished: datetime, report: FilingsReport) -> None:
        self.state["runs"] = self.state["runs"][-(RUNS_KEPT - 1) :] + [
            {
                "step": step.name if step else "daily",
                "started": started.isoformat(timespec="seconds"),
                "finished": finished.isoformat(timespec="seconds"),
                "companies": report.companies,
                "checked": len(report.checked),
                "files_saved": report.saved,
                "bytes_saved": report.bytes_saved,
                "already_there": report.present,
                "gaps": len(report.gaps),
                "failures": len(report.failures),
                "result": "complete" if report.complete else "incomplete",
            }
        ]

    def save(self, totals: dict) -> None:
        self.state["totals"] = totals
        self.state["updated"] = now_utc().astimezone().isoformat(timespec="seconds")
        self.store.replace(PROGRESS_PATH, json.dumps(self.state, indent=1, sort_keys=True).encode())
