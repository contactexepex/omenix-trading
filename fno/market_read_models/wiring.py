"""Composition root of the market read models (stories P6, P7, P9): the only place their concrete classes are wired
together (the pinned contract, the session rows, the blocks, the publisher, the run status). Moved out of
fno/composition.py, which reached the 350-line limit."""

from __future__ import annotations

import os
import subprocess
from datetime import date
from pathlib import Path

from ..ai.paths import AI_FOLDER
from ..composition import build_alert_sender
from ..config import ROOT
from ..constants import BOOKS, ENV_FNO_DB_URL, ENV_GITHUB_RUN_ATTEMPT, ENV_GITHUB_RUN_ID, RISK_PROFILE_BOOKS
from ..forecast.capture import LIVE_FOLDER
from ..forecast_scoring.wiring import SCORES_FOLDER
from ..forecast_v4_rules.series import closes_rows, regular_closes
from ..forecast_v4_rules.wiring import CLOSES_FILE
from ..models import now_utc
from ..research_data.calendar import SessionCalendar
from ..research_engine.implied_vol import SpotBlackScholes
from ..risk.profile_settings import profile_settings
from ..storage.manifest_commit import GitManifestRecorder
from ..storage.wiring import build_session_calendar, build_versioned_reader
from ..weather.wiring import build_records
from .blocks import (
    BlockBuilder,
    FnoRowsBlock,
    FnoSummaryBlock,
    IndicesBlock,
    ScreenerStocksBlock,
    ScreenerSummaryBlock,
    SectorsBlock,
)
from .chain_blocks import (
    ChainExpiriesBlock,
    ChainHistoryBlock,
    ChainRowsBlock,
    ChainSourcesBlock,
    ChainUnderlyingBlock,
    ContractHistoryBlock,
)
from .chain_session import ChainBuilder
from .contract import GitHubRawContract, PinnedContract, PublishedContract
from .db_check import DatabaseCheck, url_user
from .db_connection import VerifiedConnection
from .flows_block import FlowsBlock
from .fno_rows import FnoRowBuilder
from .followed import FollowedCompaniesFolder
from .forecast_history_block import FnoForecastHistoryBlock
from .forecast_history_inputs import ScoreReportsReader
from .forecast_lab_block import FnoForecastLabBlock
from .forecast_lab_inputs import ForecastLabReader, ProtocolFreeze, SessionsAhead
from .frame_blocks import FnoEventsBlock, IndicesIndiaBlock, SessionIndiaBlock
from .frame_inputs import FlowsReader
from .home_blocks import FnoBooksBlock, FnoPicksBlock
from .home_inputs import BooksReader, FrozenExperimentApprovals, HomeInputsReader
from .local_publisher import LocalFolderPublisher
from .market_run import MarketRun
from .page_holds import PageHoldsBlock
from .postgres_publisher import PostgresPublisher
from .publication import PRODUCT, PublicationBuilder
from .publication_inputs import PublicationInputsFile
from .publisher import ReadModelPublisher
from .run_status import LocalRunStatus, PostgresRunStatus, RunStatusRecorder
from .session_rows import SessionRowsBuilder
from .weather_block import FnoWeatherBlock
from .weather_history_block import FnoWeatherHistoryBlock
from .weather_inputs import WeatherInputsReader

CONTRACT_FOLDER = ROOT / "contracts" / "omenix-dashboard"  # the pinned W11 contract (story P6)
AZURE_POSTGRES_ROOTS = ROOT / "db" / "fno" / "azure-postgres-roots.pem"  # the CAs the publisher trusts (P6)
PUBLICATION_INPUTS = ROOT / "research" / "data" / "publications" / "publication-inputs.csv"  # judge 66
DASHBOARD_REPOSITORY = "exepex/omenix-dashboard"
FOLLOWED_COMPANIES_FOLDER = ROOT / "research" / "data" / "followed-companies" / "india"  # W11 input (judge 40)
LATEST_FROZEN_EXPERIMENT = (  # its decisive run's passing policies are the only approved strategies (P10)
    ROOT / "research" / "2026-10-12-experiment-1" / "results_challenge.json",
    "Experiment 1 (the 2019-2023 challenge)",
)


V4_FREEZE_FILE = ROOT / "research" / "forecasts" / "FREEZE_v4.md"  # G6 freeze: protocol v4's record (day, commit)


def build_market_blocks() -> list[BlockBuilder]:
    """Stories P6, P8, P9, P10 and P2a: the India blocks the contract assigns to publisher fno (Screener and Markets;
    the NIFTY option chain; Home's F&O books and picks; India's band, expiries and flows; the weather), all in one
    publication."""
    return [ScreenerSummaryBlock(), ScreenerStocksBlock(), FnoSummaryBlock(), FnoRowsBlock(), IndicesBlock(),
            SectorsBlock(), ChainUnderlyingBlock(), ChainExpiriesBlock(), ChainRowsBlock(), ChainHistoryBlock(),
            ContractHistoryBlock(), ChainSourcesBlock(), FnoBooksBlock(), FnoPicksBlock(), SessionIndiaBlock(),
            IndicesIndiaBlock(), FnoEventsBlock(), FlowsBlock(), FnoWeatherBlock(),
            FnoWeatherHistoryBlock(), FnoForecastHistoryBlock(), FnoForecastLabBlock()]  # fmt: skip


def build_pinned_contract() -> PinnedContract:
    return PinnedContract(CONTRACT_FOLDER)


def build_published_contract() -> PublishedContract:
    return GitHubRawContract(DASHBOARD_REPOSITORY)


def build_read_model_publisher(local_folder: Path | None = None) -> ReadModelPublisher:
    """A local folder when given (tests, dry runs), else the Azure fno schema with the publisher role's URL."""
    if local_folder is not None:
        return LocalFolderPublisher(local_folder)
    return PostgresPublisher(_database_url(), VerifiedConnection(AZURE_POSTGRES_ROOTS))


def build_database_check() -> DatabaseCheck:
    """`market db-check`: connects as the publisher would (TLS, pinned roots) and reads its identity and rights."""
    return DatabaseCheck(_database_url(), VerifiedConnection(AZURE_POSTGRES_ROOTS), url_user)


def _database_url() -> str:
    url = os.environ.get(ENV_FNO_DB_URL)
    if not url:
        raise RuntimeError(f"set {ENV_FNO_DB_URL} (the fno publisher role's connection string) to publish to Azure")
    return url


def build_run_status(local_folder: Path | None = None) -> RunStatusRecorder:
    """Story P7: beside the publication (a local folder's JSON lines, else the Azure `fno.run_status` table)."""
    if local_folder is not None:
        return LocalRunStatus(local_folder, PRODUCT)
    return PostgresRunStatus(_database_url(), VerifiedConnection(AZURE_POSTGRES_ROOTS), PRODUCT)


def build_market_run(cfg: dict, local_folder: Path | None = None) -> MarketRun:
    """Stories P6, P7: the archived NSE files in Drive, the pinned contract, the publisher and the run status (a local
    folder when given, else Azure), #fno-desk alerts."""
    contract = build_pinned_contract()
    publications = PublicationBuilder(build_market_blocks(), contract, repository_commit(), holds_page=PageHoldsBlock())
    rows = build_session_rows_builder(cfg)
    publisher, status = build_read_model_publisher(local_folder), build_run_status(local_folder)
    return MarketRun(build_session_calendar(), contract, rows, publications, publisher, build_alert_sender(), status,
                     run_id, build_publication_inputs(local_folder))  # fmt: skip


def build_publication_inputs(local_folder: Path | None = None) -> PublicationInputsFile:
    """Judge 66: the flows copies each publication read, beside a local publication, else committed here."""
    if local_folder is not None:
        return PublicationInputsFile(local_folder / PUBLICATION_INPUTS.name)
    return PublicationInputsFile(PUBLICATION_INPUTS, GitManifestRecorder(ROOT, PUBLICATION_INPUTS.parent).commit)


def run_id(env=os.environ, clock=lambda: now_utc()) -> str:
    """GitHub's run ID and attempt (a re-run is its own run), else the local time."""
    if env.get(ENV_GITHUB_RUN_ID):
        return f"gh-{env[ENV_GITHUB_RUN_ID]}-{env.get(ENV_GITHUB_RUN_ATTEMPT, '1')}"
    return f"local-{clock():%Y%m%dT%H%M%S%fZ}"


def build_session_rows_builder(cfg: dict) -> SessionRowsBuilder:
    """A session's rows from the archived NSE files in Drive (ATM IV: Black-Scholes on the spot, as W11's examples).
    Publishing reads NSE's latest version of each file (A11's revisions; judge 49); research reads point in time."""
    fno_rows = FnoRowBuilder(SpotBlackScholes(), cfg["risk_free_rate"])
    followed = FollowedCompaniesFolder(FOLLOWED_COMPANIES_FOLDER)
    chain = ChainBuilder(cfg["risk_free_rate"])
    profile = profile_settings(cfg, RISK_PROFILE_BOOKS)
    books = BooksReader(ROOT, BOOKS, profile.paper_account_rs)
    home = HomeInputsReader(books, FrozenExperimentApprovals(*LATEST_FROZEN_EXPERIMENT), profile.open_risk_cap_rs)
    store, calendar = build_versioned_reader(), build_session_calendar()
    flows = FlowsReader(store, calendar)
    reports = ScoreReportsReader(ROOT / SCORES_FOLDER)
    return SessionRowsBuilder(store, calendar, fno_rows, followed, chain, home, flows, build_weather_inputs(), reports,
                              build_forecast_lab_inputs(calendar))  # fmt: skip


def build_forecast_lab_inputs(calendar: SessionCalendar) -> ForecastLabReader:
    """Story P2b: G4's committed reports and the committed live and AI forecast records (G3, F1); protocol v4's freeze
    from its committed record (G6 freeze)."""
    folders = [ROOT / LIVE_FOLDER, ROOT / AI_FOLDER]
    return ForecastLabReader(ScoreReportsReader(ROOT / SCORES_FOLDER), folders, SessionsAhead(calendar), v4_freeze)


def v4_freeze(path: Path = V4_FREEZE_FILE) -> ProtocolFreeze | None:
    """`FREEZE_v4.md`'s `Frozen on:` day and protocol commit, or None while the record does not exist."""
    from ..forecast_scoring.v4.freeze_check import PROTOCOL_COMMIT
    from ..forecast_scoring.v4.records import FROZEN_ON

    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    day, commit = FROZEN_ON.search(text), PROTOCOL_COMMIT.search(text)
    if day is None or commit is None:
        raise ValueError(f"{path.name} has no 'Frozen on:' or no 'Protocol commit:' line")
    return ProtocolFreeze(date.fromisoformat(day.group(1)), commit.group(1))


def build_weather_inputs() -> WeatherInputsReader:
    """Story P2a: M1's committed weather records and NIFTY's committed closes (O6), both in this repository."""
    return WeatherInputsReader(build_records(), regular_closes(closes_rows(CLOSES_FILE.read_text())))


def repository_commit() -> str:
    """The commit of the code that builds (each publication names it)."""
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True)
    return head.stdout.strip() or "unknown"
