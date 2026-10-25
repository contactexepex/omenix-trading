"""Composition root of story G13d: G13's 3 pm records and G13d's own files through O9's Drive store and verified
cache, the NSE calendar, G13b's seal check (GitHub push time) with G13d's own deadline, and O1's `live_from` date."""

from __future__ import annotations

import os
from datetime import date, datetime
from pathlib import Path

from ..models import IST, now_ist
from ..price_distribution.method import FNO
from ..price_distribution.method import method_sha256 as files_sha256
from ..price_distribution.store import DriveDistributionStore
from ..price_ranges.seals import Seals
from ..price_ranges.wiring import build_seal_check
from ..storage.data_wiring import DRIVE_CACHE_FOLDER, build_data_store
from ..storage.wiring import REPOSITORY, build_owner_drive, build_session_calendar
from .constants import DEADLINE
from .folders import live_path, receipt_file, seal_path
from .issuer import PremiumIssuer

STEP = "premium_ranges"  # O1's step name and its `daily.live_from` key
WRITER = "premrange"
UNDERLYINGS = ("NIFTY", "BANKNIFTY")
NO_DRIVE = "set the four FNO_GDRIVE_* owner settings to use G13d's Drive data store"
PACKAGE = Path(__file__).resolve().parent
OWN = ("build", "constants", "report", "rule", "scores", "sessions")
IMPORTED = ("price_distribution/pricing.py", "price_distribution/scoring.py", "forecast_scoring/block_bootstrap.py",
            "research_engine/implied_vol.py")  # fmt: skip
METHOD_FILES = (*(PACKAGE / f"{name}.py" for name in OWN), *(FNO / path for path in IMPORTED))


def method_sha256() -> str:
    return files_sha256(METHOD_FILES)


def live_from(cfg: dict) -> date | None:
    raw = (cfg.get("daily", {}).get("live_from", {}) or {}).get(STEP)
    return date.fromisoformat(str(raw)) if raw else None


def data_root() -> Path:
    return REPOSITORY / DRIVE_CACHE_FOLDER / "data"


def same_day_close(calendar, day: date) -> datetime:
    """15:30 IST of the issue day itself (story: sealed before any later price of d is known)."""
    return datetime.combine(day, DEADLINE, IST)


def build_store(env=os.environ) -> DriveDistributionStore:
    drive = build_owner_drive(env)
    if drive is None:
        raise RuntimeError(NO_DRIVE)
    return DriveDistributionStore(drive, build_data_store(WRITER, env=env))


def build_seals(store) -> Seals:
    return Seals(build_seal_check(deadline_of=same_day_close), store, receipt_file, now_ist, live_path, seal_path)


def build_issuer(cfg: dict, store=None, before=None) -> PremiumIssuer:
    from ..rehearsal.live_wiring import rehearsed_date

    store = store or build_store()
    live = rehearsed_date(STEP, live_from(cfg))  # REH1o
    return PremiumIssuer(store, build_session_calendar(), UNDERLYINGS, live, now_ist, method_sha256(),
                         before or (lambda day: []))  # fmt: skip
