"""Composition root of the daily health check (story O8): the repository's files and history, F1's GitHub push
receipts, the NSE calendar, the desk timetable from config.yaml, the run record and the #fno-desk alert sender. Another
evidence source or receipt source is one new class plus one line here.
Story O10 adds the capture-error log and GitHub's Actions runs."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

from ..ai.receipts import GitHubActivityReceipts
from ..config import ROOT
from ..constants import DEFAULT_REPOSITORY, ENV_GITHUB_TOKEN, GITHUB_REPOSITORY_VARIABLE, HEALTH_RUNS_FILE
from ..desk.timetable import timetable_from_config
from ..research_data.calendar import load_session_calendar
from ..storage.wiring import CALENDAR_FILE
from .capture_errors import CAPTURE_ERRORS_FILE, CaptureErrorLog
from .checker import HealthCheck
from .evidence import Evidence, HealthHistory
from .expectations import build_expectations
from .horizon import HORIZON_MARKER, CalendarHorizon
from .run_failures import GitHubRuns, RunSource
from .run_record import RunRecord


def build_run_record(root: Path = ROOT) -> RunRecord:
    return RunRecord(Path(root) / HEALTH_RUNS_FILE)


def build_capture_error_log(root: Path = ROOT) -> CaptureErrorLog:
    return CaptureErrorLog(Path(root) / CAPTURE_ERRORS_FILE)


def build_run_source(env: Mapping[str, str] = os.environ) -> RunSource:
    repository = env.get(GITHUB_REPOSITORY_VARIABLE) or DEFAULT_REPOSITORY
    return GitHubRuns(repository, env.get(ENV_GITHUB_TOKEN, ""))


def build_health_check(cfg: dict, root: Path = ROOT, env: Mapping[str, str] = os.environ) -> HealthCheck:
    history = HealthHistory(Path(root))
    from ..rehearsal.receipts_wiring import rehearsed_receipts

    receipts = rehearsed_receipts(
        GitHubActivityReceipts(env.get(GITHUB_REPOSITORY_VARIABLE, ""), env.get(ENV_GITHUB_TOKEN, ""), history), history
    )  # REH1b: the rehearsal's push log
    evidence = Evidence(Path(root), history, receipts)
    expectations = build_expectations(evidence, Path(root), timetable_from_config(cfg))
    calendar, settings = load_session_calendar(CALENDAR_FILE), cfg["health"]
    horizon = CalendarHorizon(calendar.last, calendar.calendar_sha256(), Path(root) / HORIZON_MARKER,
                              settings["calendar_horizon_days"])  # fmt: skip
    return HealthCheck(expectations, calendar, build_run_record(root), settings["window_days"], horizon)
