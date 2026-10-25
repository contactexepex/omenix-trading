"""Composition root of the daily trade card (story T1): the only place that picks the card's concrete sources, sender,
stores and clocks. Swapping Slack, Drive, the weather model or the forecasters changes this file only."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from ..ai.history import RepoHistory
from ..ai.receipts import GitHubActivityReceipts
from ..config import ROOT
from ..constants import (
    CARDS_AREA,
    DEFAULT_REPOSITORY,
    ENV_FNO_SLACK_BOT_TOKEN,
    ENV_GITHUB_TOKEN,
    FNO_DESK_CHANNEL_ID,
    GITHUB_REPOSITORY_VARIABLE,
)
from ..models import now_utc
from ..server_clock import GITHUB_TIME_URL, HttpDateClock
from ..storage import wiring as storage
from ..storage.raw_store import AreaStore
from .card import CardBuilder
from .card_clocks import GITHUB, CardClocks, ServerCardClocks
from .committed import DownloadedRecords, GitHeadRecords
from .daily import DailyCard
from .deliveries import RepoDeliveryFiles
from .forecasts import LiveCaptureForecasts
from .issue import CardIssuer
from .posting import CardPoster, NoCardPoster, SlackCardPoster
from .problem_steps import ProblemSteps
from .record_store import CardRecordStore, DriveCardRecords, NoCardRecords
from .recorded_weather import RecordedWeather
from .render import SlackTextRenderer
from .rule_checks import DecisionOutcome, ExecutionOutcome, RunLogReader
from .ruled_status import RuleChecks, RuledStatus
from .session import SessionCheck
from .status import RegistryStatus
from .witness import IssuanceWitness

# Its `Date` header is GitHub's server time (no sign-in needed). A repository path, not the API root: the cloud
# sessions' GitHub proxy answers the root itself (HTTP 400, no Date header), found on the live test post of 15 Oct


def _repository(env) -> str:
    return env.get(GITHUB_REPOSITORY_VARIABLE) or DEFAULT_REPOSITORY


def _host_now() -> datetime:
    return now_utc()


def build_daily_card(root: Path = ROOT) -> DailyCard:
    records = GitHeadRecords(root)
    status = build_status(records, root)
    builder = CardBuilder(status, _weather(records), LiveCaptureForecasts(records), status.problems)  # T1e: one reader
    return DailyCard(SessionCheck(records), builder, SlackTextRenderer(), RepoDeliveryFiles(root, records))


def _weather(records) -> RecordedWeather:
    """M1's record path for a day, relative to the repository: the card reads the committed record (story T1c)."""
    from ..weather.records import WeatherRecords
    from ..weather.wiring import WEATHER_FOLDER

    folder = WEATHER_FOLDER.relative_to(ROOT)
    return RecordedWeather(records, lambda day: WeatherRecords(folder).path(day).as_posix())


def build_status(records: GitHeadRecords, root: Path = ROOT) -> RuledStatus:
    """T1's registry status (accounts from Drive's download, E2c) with T2's rule outcomes; the final times come from
    the desk's own timetable."""
    from ..config import load_app_config
    from ..desk.timetable import timetable_from_config

    timetable, runs = timetable_from_config(load_app_config()), RunLogReader(records)
    previous = SessionCheck(records)
    rules = (
        DecisionOutcome(records, runs, timetable),
        ExecutionOutcome(runs, timetable, lambda d: previous.answer(d).previous),
    )
    return RuledStatus(RegistryStatus(records, DownloadedRecords(root)), RuleChecks(rules), ProblemSteps(runs))


def build_card_poster(env=os.environ) -> CardPoster:
    """#fno-desk with `FNO_SLACK_BOT_TOKEN` only; without it nothing is sent and the outcome says so."""
    token = env.get(ENV_FNO_SLACK_BOT_TOKEN)
    from ..rehearsal.card_label import rehearsed_card_poster

    return rehearsed_card_poster(SlackCardPoster(token, FNO_DESK_CHANNEL_ID) if token else NoCardPoster())


def build_card_records(env=os.environ) -> CardRecordStore:
    """The `cards` area of the owner's Drive project folder (owner OAuth settings), or a store that says why not."""
    try:
        drive = storage.build_owner_drive(env)
    except Exception as error:  # noqa: BLE001 - a refused sign-in must not stop the card; named by type only
        return NoCardRecords(f"Drive sign-in failed ({type(error).__name__})")
    return NoCardRecords() if drive is None else DriveCardRecords(AreaStore(drive, CARDS_AREA))


def build_card_clocks(env=os.environ) -> CardClocks:
    """Slack's and GitHub's server times; a rehearsal's form instead (T1f), which never builds the GitHub client."""
    from ..rehearsal.card_label import rehearsed_card_clocks

    def real() -> CardClocks:
        return ServerCardClocks([HttpDateClock(GITHUB, GITHUB_TIME_URL.format(repository=_repository(env)))], _host_now)

    return rehearsed_card_clocks(real, env)


def build_card_issuer(env=os.environ, root: Path = ROOT) -> CardIssuer:
    records = GitHeadRecords(root)
    deliveries = RepoDeliveryFiles(root, records)
    return CardIssuer(
        build_card_poster(env), build_card_records(env), deliveries, build_card_clocks(env), _host_now,
        records.code_commit(),
    )  # fmt: skip


def build_issuance_witness(env=os.environ, root: Path = ROOT) -> IssuanceWitness:
    history = RepoHistory(root)
    from ..rehearsal.receipts_wiring import rehearsed_receipts

    receipts = rehearsed_receipts(
        GitHubActivityReceipts(_repository(env), env.get(ENV_GITHUB_TOKEN, ""), history), history
    )  # REH1b: the rehearsal's push log
    return IssuanceWitness(RepoDeliveryFiles(root, GitHeadRecords(root)), history, receipts)
