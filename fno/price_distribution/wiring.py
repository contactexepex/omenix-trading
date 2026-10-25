"""Composition root of story G13: the 3 pm chains (A4's quote store), the panel for the end-of-day back-fill, the NSE
calendar, the committed closes, config's rate, O9's Drive data store and cache, and O1's `live_from` date."""

from __future__ import annotations

import os
from datetime import date

from ..constants import NIFTY_SYMBOL, RECORDED_INDEX_OPTIONS
from ..forecast_v4_rules.series import closes_rows, regular_closes
from ..forecast_v4_rules.wiring import CLOSES_FILE
from ..models import now_ist
from ..research_data.panel_reader import read_nifty_panel
from ..storage.data_wiring import DRIVE_CACHE_FOLDER, build_data_store, build_drive_cache
from ..storage.wiring import PANEL_FOLDER, REPOSITORY, build_owner_drive, build_quote_store, build_session_calendar
from .backfill import Backfill
from .build import DayBuilder
from .constants import SOURCE_GROWW, SOURCE_NSE
from .method import method_sha256
from .recorder import LiveRecorder
from .sources import PanelEodChains, SnapshotChains
from .store import DriveDistributionStore

STEP = "price_distribution"  # O1's step name and its `daily.live_from` key
WRITER = "pricedist"
UNDERLYINGS = (NIFTY_SYMBOL, *RECORDED_INDEX_OPTIONS)
NO_DRIVE = "set the four FNO_GDRIVE_* owner settings to use G13's Drive data store"


def live_from(cfg: dict) -> date | None:
    raw = (cfg.get("daily", {}).get("live_from", {}) or {}).get(STEP)
    return date.fromisoformat(str(raw)) if raw else None


def _regular_closes():
    return regular_closes(closes_rows(CLOSES_FILE.read_text(encoding="utf-8")))


def build_closes() -> dict[date, float]:
    """The committed NIFTY closes the scorer resolves targets with."""
    return {c.day: c.value for c in _regular_closes()}


def build_day_builder(cfg: dict) -> DayBuilder:
    return DayBuilder(build_session_calendar(), float(cfg["risk_free_rate"]), _regular_closes(), method_sha256())


def build_store(env=os.environ) -> DriveDistributionStore:
    drive = build_owner_drive(env)
    if drive is None:
        raise RuntimeError(NO_DRIVE)
    return DriveDistributionStore(drive, build_data_store(WRITER, env=env))


def build_chains(sources=(SOURCE_GROWW, SOURCE_NSE)) -> SnapshotChains:
    return SnapshotChains(build_quote_store(), sources)


def build_live_recorder(cfg: dict) -> LiveRecorder:
    from ..rehearsal.live_wiring import rehearsed_date

    live = rehearsed_date(STEP, live_from(cfg))  # REH1o
    return LiveRecorder(build_chains(), build_day_builder(cfg), build_store(), build_session_calendar(), UNDERLYINGS,
                        live, now_ist)  # fmt: skip


def build_backfill(cfg: dict, eod: bool, years=None) -> Backfill:
    source = PanelEodChains(read_nifty_panel(PANEL_FOLDER, years)) if eod else build_chains()
    return Backfill(source, build_day_builder(cfg), build_store(), build_session_calendar(), live_from(cfg))


def build_score_inputs():
    """The Drive cache (synced by the command) and its local root, the store for the report."""
    return build_drive_cache(), REPOSITORY / DRIVE_CACHE_FOLDER, build_store()
