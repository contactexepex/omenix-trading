"""Composition root of story G13b: A4's and A4c's chains, G13's panel and the archived F&O and index-close files for
the back-fill, the NSE calendar, NIFTY's committed closes and BANKNIFTY's Drive table, config's rate, O9's Drive store
and cache, O8's GitHub push evidence for the seal, and O1's `live_from` date."""

from __future__ import annotations

import os
from datetime import date, timedelta

from ..ai.receipts import GitHubActivityReceipts
from ..config import ROOT
from ..constants import DEFAULT_REPOSITORY, ENV_GITHUB_TOKEN, GITHUB_REPOSITORY_VARIABLE, NIFTY_SYMBOL, PUBLISH_BRANCH
from ..forecast_v4_rules.wiring import CLOSES_FILE
from ..health.evidence import Evidence, HealthHistory
from ..models import now_ist
from ..price_distribution.horizons import previous_regular_session
from ..price_distribution.sources import PanelEodChains, SnapshotChains
from ..price_distribution.store import DriveDistributionStore
from ..research_data.panel_reader import read_nifty_panel
from ..research_engine.ledger import Git
from ..storage.data_wiring import DRIVE_CACHE_FOLDER, build_data_store, build_drive_cache, receipt_folder
from ..storage.wiring import (
    PANEL_FOLDER,
    REPOSITORY,
    build_nifty_panel_files,
    build_owner_drive,
    build_quote_store,
    build_session_calendar,
    build_stored_index_close_files,
)
from .backfill import RangeBackfill
from .bhavcopy_chains import BhavcopyChains
from .build import RangeBuilder
from .chains import RoutedChains
from .closes import CommittedNiftyCloses, IndexFileCloses, TableCloses
from .constants import ISSUE_1545, UNDERLYINGS
from .folders import live_path
from .issuer import RangeIssuer
from .method import method_sha256
from .reader import receipt_file
from .sealing import SealCheck
from .seals import Seals, seal_recent
from .tables import CloseTables

STEP = "price_ranges"  # O1's step name and its `daily.live_from` key
WRITER = "pricerange"
BANKNIFTY = "BANKNIFTY"
NO_DRIVE = "set the four FNO_GDRIVE_* owner settings to use G13b's Drive data store"
CACHE_ROOT = REPOSITORY / DRIVE_CACHE_FOLDER
SEAL_READ_ATTEMPTS = 3  # a failed evidence read, read again twice within the run (story receipts-reach)


def live_from(cfg: dict) -> date | None:
    raw = (cfg.get("daily", {}).get("live_from", {}) or {}).get(STEP)
    return date.fromisoformat(str(raw)) if raw else None


def build_store(env=os.environ) -> DriveDistributionStore:
    drive = build_owner_drive(env)
    if drive is None:
        raise RuntimeError(NO_DRIVE)
    return DriveDistributionStore(drive, build_data_store(WRITER, env=env))


def build_tables(store) -> CloseTables:
    return CloseTables(store, receipt_folder(), build_drive_cache())


def build_closes(tables: CloseTables) -> TableCloses:
    return TableCloses(tables.latest_text, CommittedNiftyCloses(lambda: CLOSES_FILE.read_text(encoding="utf-8")))


def build_builder(cfg: dict) -> RangeBuilder:
    return RangeBuilder(build_session_calendar(), float(cfg["risk_free_rate"]), method_sha256())


def build_seals(store) -> Seals:
    return Seals(build_seal_check(), store, receipt_file, now_ist)


def seal_lines(seals: Seals, store, day: date) -> list[str]:
    """The final seals of the last 8 days' live issues, recorded while GitHub's 7-day log still has them."""
    return seal_recent(seals, lambda u, d, issue: store.get(live_path(u, d, issue)) is not None, UNDERLYINGS,
                       ISSUE_1545, day)  # fmt: skip


def build_issuer(cfg: dict) -> RangeIssuer:
    from ..rehearsal.live_wiring import rehearsed_date

    live = rehearsed_date(STEP, live_from(cfg))  # REH1o
    store, calendar = build_store(), build_session_calendar()
    tables, seals = build_tables(store), build_seals(store)
    index_closes = IndexFileCloses(build_stored_index_close_files(), calendar)

    def update_banknifty(day: date) -> list[str]:
        lines = tables.update(BANKNIFTY, index_closes, previous_regular_session(calendar, day))
        return lines + seal_lines(seals, store, day)

    return RangeIssuer(SnapshotChains(build_quote_store()), build_builder(cfg), build_closes(tables).closes, store,
                       calendar, UNDERLYINGS, live, now_ist, update_banknifty)  # fmt: skip


def build_backfill(cfg: dict, eod: bool, years=None) -> RangeBackfill:
    store, calendar = build_store(), build_session_calendar()
    if eod:
        fo_files, _ = build_nifty_panel_files()
        chains = RoutedChains({NIFTY_SYMBOL: PanelEodChains(read_nifty_panel(PANEL_FOLDER, years)),
                               BANKNIFTY: BhavcopyChains(fo_files)})  # fmt: skip
    else:
        chains = SnapshotChains(build_quote_store())
    return RangeBackfill(chains, build_builder(cfg), build_closes(build_tables(store)).closes, store, calendar,
                         live_from(cfg))  # fmt: skip


def build_table_update() -> tuple[CloseTables, IndexFileCloses]:
    calendar = build_session_calendar()
    return build_tables(build_store()), IndexFileCloses(build_stored_index_close_files(), calendar)


def deep_enough(root=ROOT, days: int = 10) -> None:
    """In a shallow clone, git's "first commit adding the file" is the clone's boundary commit, so the push time
        found would be wrong: the history of the last `days` days is fetched first (review finding 1). Through B4's
    `Git`, so a failure raises instead of passing as "not shallow" or a fetch that never happened."""
    git = Git(root)
    if git.is_shallow():  # a failed read or fetch raises GitFailed: a wrong push time would seal a record wrongly
        git.deepen_since(now_ist().date() - timedelta(days=days), PUBLISH_BRANCH)


def build_seal_check(env=os.environ, deadline_of=None) -> SealCheck:
    """`deadline_of`: G13b's 15:45 deadline when None; G13d passes its own (`fno/premium_ranges/wiring.py`)."""
    deep_enough()
    history = HealthHistory(ROOT)
    repository = env.get(GITHUB_REPOSITORY_VARIABLE) or DEFAULT_REPOSITORY
    from ..rehearsal.receipts_wiring import rehearsed_receipts

    receipts = rehearsed_receipts(
        GitHubActivityReceipts(repository, env.get(ENV_GITHUB_TOKEN, ""), history), history
    )  # REH1b: the rehearsal's push log
    return SealCheck(Evidence(ROOT, history, receipts).file_pushed_at, build_session_calendar(), deadline_of,
                     attempts=SEAL_READ_ATTEMPTS)  # fmt: skip
