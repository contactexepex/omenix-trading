"""The one table of what the health check expects (story O8): each row names a job, the check that reads its evidence,
the sessions it runs on and the first session it is live for (`None`: not live yet, so silent).

Deadlines are the owners' objects (`LATEST_START`, `GENERATION_DEADLINE`, `receipt_deadline` inside the AI check, the
desk timetable). The five below exist nowhere else in `fno/`; each is derived from its workflow's cron and is listed
for step 5's timing-consistency test."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time
from pathlib import Path

from ..ai.timing import LATEST_START
from ..constants import AI_BOOKS, BOOK_DISPLAY_NAMES, FORECAST_QUESTIONS, FORECASTERS, SESSION_MUHURAT
from ..desk.timetable import Timetable
from ..forecast.schema_v2 import GENERATION_DEADLINE
from ..preopen.day_row import PREOPEN_RECEIPT_BY
from ..quotes.recorder import DATASET, NSE_DATASET, RECORDED_SESSION_KINDS
from .data_checks import PanelDayCheck, SessionRowCheck
from .desk_checks import MarksCheck, RunLogCheck
from .evidence import Evidence
from .forecast_checks import AiBookCheck, ForecastRowsCheck
from .model import Deadline, SessionCheck
from .preopen_checks import PreopenCheck
from .quote_checks import CanonicalCheck

A8_RELEASE_BY = Deadline(time(23, 30))  # participant-oi-release.yml: its 22:45 run watches until 23:30
INDEX_CLOSE_BY = Deadline(time(12, 0), days_after=1)  # index-closes.yml: after its last retry, 11:41 the next day
PANEL_DAY_BY = Deadline(time(13, 0), days_after=1)  # panel-days.yml: after its retry, 12:11 the next day
# flows-download.yml runs at 21:10, but the session's row reaches the manifest only after that run (4 h late on 14 Oct)
# or the next morning's market publish (07:10): 12:00 the next day, as the closes (measured, response 153 addendum 2)
FLOWS_BY = Deadline(time(12, 0), days_after=1)
# flow-history.yml (A23): 21:30 and a 07:15 retry the next day; due before the next morning's session (09:15)
FLOW_HISTORY_BY = Deadline(time(9, 0), days_after=1)

PARTICIPANT_OI_MANIFEST = "research/data/manifests/participant-oi.csv"
CLOSES_FILE = "research/data/nifty-panel/warmup_closes.csv"
PANEL_MANIFEST = "research/data/nifty-panel/manifest.json"
FLOWS_MANIFEST = "research/data/manifests/fii-dii-cash-by-session.csv"
FLOW_HISTORY_MANIFESTS = {"A23 participant volume": "research/data/manifests/participant-volume.csv",
                          "A23 FII statistics": "research/data/manifests/fii-stats.csv"}  # fmt: skip
INTRADAY_FOLDER = "research/data/intraday"
ALL_SESSION_KINDS = (*RECORDED_SESSION_KINDS, SESSION_MUHURAT)  # NSE publishes the evening files for muhurat too
FIRST_RECORDED, FIRST_SEALED, DATA_JOBS_FROM = date(2026, 10, 14), date(2026, 10, 15), date(2026, 10, 13)
FLOW_HISTORY_FROM = date(2026, 10, 22)  # A23: flow-history.yml's first scheduled run entered this session (addendum 2)
# A16's marks are checked from the first session after the 16 Oct trial days (a late first fire; duplicate takers);
# the table never listed it, so 23 Oct's three lost marks were reported by nothing in the evening check (story A16i)
MARKS_FROM = date(2026, 10, 19)


@dataclass(frozen=True)
class Expectation:
    name: str
    check: SessionCheck
    kinds: tuple[str, ...]  # the session kinds this job runs on; others are `not expected`
    live_from: date | None  # None: not live yet (silent)

    def expected_on(self, session: date, kind: str) -> bool:
        return self.live_from is not None and session >= self.live_from and kind in self.kinds


def expected_forecast_rows() -> int:
    """Book 1 and the baselines answer every question; the AI books' rows live in their own files."""
    return len([f for f in FORECASTERS if f not in AI_BOOKS]) * len(FORECAST_QUESTIONS)


def build_expectations(evidence: Evidence, root: Path, timetable: Timetable) -> list[Expectation]:
    recorded, everything = RECORDED_SESSION_KINDS, ALL_SESSION_KINDS
    return [
        Expectation("3 pm Groww recorder", CanonicalCheck(evidence, DATASET, Deadline(LATEST_START)), recorded,
                    FIRST_RECORDED),
        Expectation("NSE recorder", CanonicalCheck(evidence, NSE_DATASET, Deadline(LATEST_START)), recorded,
                    FIRST_RECORDED),
        Expectation("Forecast v2 records",
                    ForecastRowsCheck(evidence, expected_forecast_rows(), Deadline(GENERATION_DEADLINE)), recorded,
                    FIRST_RECORDED),
        *[Expectation(f"{BOOK_DISPLAY_NAMES[book]} sealed forecast", AiBookCheck(evidence, book), recorded,
                      FIRST_SEALED) for book in AI_BOOKS],
        Expectation("Desk daily run", RunLogCheck(root, Deadline(timetable.decision_deadline)), recorded, None),
        Expectation("A16 15-minute marks", MarksCheck(root / INTRADAY_FOLDER), recorded, MARKS_FROM),
        Expectation("A22 pre-open data", PreopenCheck(evidence, Deadline(PREOPEN_RECEIPT_BY)), recorded, None),
        Expectation("A8 participant OI", SessionRowCheck(evidence, PARTICIPANT_OI_MANIFEST, A8_RELEASE_BY),
                    everything, DATA_JOBS_FROM),
        Expectation("Index closes", SessionRowCheck(evidence, CLOSES_FILE, INDEX_CLOSE_BY), everything,
                    DATA_JOBS_FROM),
        Expectation("NIFTY panel day", PanelDayCheck(evidence, PANEL_MANIFEST, PANEL_DAY_BY), everything,
                    DATA_JOBS_FROM),
        Expectation("FII/DII flows", SessionRowCheck(evidence, FLOWS_MANIFEST, FLOWS_BY), everything,
                    DATA_JOBS_FROM),
        *[Expectation(name, SessionRowCheck(evidence, path, FLOW_HISTORY_BY), everything, FLOW_HISTORY_FROM)
          for name, path in FLOW_HISTORY_MANIFESTS.items()],
    ]  # fmt: skip
