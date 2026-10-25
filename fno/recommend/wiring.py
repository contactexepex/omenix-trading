"""Composition root of `fno/recommend/` (story REC1b): the two candidate sources (Book 1's decision runs, the school's
dashcam), the versions' evidence (D6's school rows, the playbook registry, MS-P1h's counting rule, GitHub's push
receipts), the day's conditions (the run log, M1's weather), the write-once Drive store with its pushed receipts, and
the #fno-desk alert sender. Drive and the push log are the rehearsal's in a rehearsal (REH1), through their builders."""

from __future__ import annotations

import hashlib
import os
from datetime import date, datetime
from pathlib import Path

from ..ai.activity_log import ReceiptUnknown
from ..ai.history import RepoHistory
from ..ai.receipts import GitHubActivityReceipts
from ..config import ROOT
from ..constants import (
    DEFAULT_REPOSITORY,
    ENV_GITHUB_TOKEN,
    GITHUB_REPOSITORY_VARIABLE,
    JOURNAL_FOLDER,
    PLAYBOOK_FOLDER,
    PLAYBOOK_REGISTRY_FILE,
    PlaybookStatus,
)
from ..models import now_utc
from ..playbook.registry import parse_rows
from ..research_engine.ledger import Git
from ..storage.data_wiring import DATA_AREA, RECEIPTS_FOLDER, REPOSITORY, build_data_store, receipt_folder
from ..storage.manifest_commit import GitManifestRecorder
from ..storage.receipt_publisher import GitReceiptPublisher
from ..storage.trading_days import is_trading_day
from ..storage.wiring import build_session_calendar
from ..weather.records import WeatherRecords
from ..weather.wiring import WEATHER_FOLDER
from .conditions import RunLogConditions
from .desk_source import DeskSource
from .evidence import NoEligibility, RecommenderEvidence
from .gather import Header, Ports
from .run import RecommendRun
from .school_source import SchoolSource
from .store import AREA_FOLDER, DriveRecommendations

WRITER = "recommender"
RECEIPTS_MESSAGE = "Receipts: the recommender's records ({what})"
RECEIPTS_LABEL = "recommendation receipts"
CONFIG_FILE = "config.yaml"


def build_recommend_run(cfg: dict, root: Path = ROOT, env=os.environ) -> RecommendRun:
    from ..composition import build_alert_sender, build_versions
    from ..rehearsal.receipts_wiring import rehearsed_receipts
    from ..school.dashcam.wiring import build_dashcam
    from ..school.registration.wiring import build_counting_rule
    from ..school.settings import school_settings

    dashcam, versions = build_dashcam(env=env), build_versions(root)
    history, repository = RepoHistory(root), env.get(GITHUB_REPOSITORY_VARIABLE) or DEFAULT_REPOSITORY
    receipts = rehearsed_receipts(GitHubActivityReceipts(repository, env.get(ENV_GITHUB_TOKEN, ""), history),
                                  history)  # fmt: skip

    def receipt_of(commit: str) -> datetime | None:
        try:
            return receipts.received_at(commit)
        except ReceiptUnknown:  # GitHub cannot answer: the session does not count that day (judge 620.2 m2)
            return None

    evidence = RecommenderEvidence(
        lambda: [row.book for row in versions.rows], lambda: _at_paper(root),
        school_settings(cfg).first_counted,
        trading_sessions(),
        dashcam, build_counting_rule(Git(root), versions), receipt_of,
    )  # fmt: skip
    ports = Ports((DeskSource(root, root / JOURNAL_FOLDER), SchoolSource(root, dashcam)), evidence,
                  RunLogConditions(root, WeatherRecords(WEATHER_FOLDER)), NoEligibility())  # fmt: skip
    return RecommendRun(root, ports, _store(env), build_alert_sender(), lambda: _header(root), now_utc)


def is_session(day: date) -> bool:
    return is_trading_day(build_session_calendar(), day)


def _store(env) -> DriveRecommendations:
    return DriveRecommendations(build_data_store(WRITER, None, env), build_receipt_publisher())


def build_receipt_publisher() -> GitReceiptPublisher:
    """The recommender's receipts (the records and their checks), committed and pushed to `main`."""
    folder = REPOSITORY / RECEIPTS_FOLDER / DATA_AREA / AREA_FOLDER  # only the recommender's receipts
    recorder = GitManifestRecorder(REPOSITORY, folder, message=RECEIPTS_MESSAGE, label=RECEIPTS_LABEL)
    return GitReceiptPublisher(recorder, receipt_folder(), REPOSITORY)


def trading_sessions():
    """NSE's trading sessions from a to b, both included (muhurat-only days are not trading sessions)."""
    calendar = build_session_calendar()
    return lambda start, end: [d for d in calendar.sessions(start, end) if is_trading_day(calendar, d)]


def _header(root: Path) -> Header:
    config = hashlib.sha256((root / CONFIG_FILE).read_bytes()).hexdigest()
    return Header(Git(root).head(), config)


def _at_paper(root: Path) -> list[str]:
    """`name@version` of each playbook version whose latest registry row is `paper` (D1: the latest row decides)."""
    rows = parse_rows((root / PLAYBOOK_FOLDER / PLAYBOOK_REGISTRY_FILE).read_text(encoding="utf-8"))
    latest = {(row.name, row.version): row for row in rows}
    return [f"{name}@{version}" for (name, version), row in latest.items() if row.status == PlaybookStatus.PAPER]
