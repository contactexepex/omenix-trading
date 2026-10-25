"""Composition root of the candle back-fill (story A16b): the only place that picks Groww (through A16's
`ReadOnlyGroww`), the owner's Drive, NSE's index-close archive, the repository folders and the realised-variance
strategy. A16's `wiring.py` is not touched. A dry run reads Groww, Drive and NSE live but writes every file under a
folder outside the repository and archives nothing in Drive."""

from __future__ import annotations

from pathlib import Path

from ..global_cues.cue_calendars import NseSessionCalendar
from ..models import now_ist
from ..providers.groww import GrowwProvider
from ..storage.raw_library import RawFileLibrary
from ..storage.raw_source import NseIndexCloseSource
from ..storage.raw_store import AreaStore, LocalFolderStore, RawFileStore
from ..storage.wiring import (
    MANIFEST_FOLDER,
    OWNER_UPLOAD_SETTINGS,
    RAW_AREA,
    build_nse_source,
    build_owner_drive,
    build_owner_drive_store,
    build_raw_stores,
    build_session_calendar,
)
from .backfill import SERIES_START, CandleBackfill
from .backfill_daily import CANDLE_FOLDER, DEFERRALS, MANIFESTS
from .backfill_verify import CandleRowVerifier
from .candle_archive import CandleArchive
from .candle_rv_table import CandleRvTable
from .candle_source import GrowwCandleSource
from .deferral_log import DeferralLog
from .nse_days import NseIndexDays
from .read_only import ReadOnlyGroww
from .realised_vol import CandleCloseRv15m
from .session_deriver import SessionDeriver

DRY_RUN_DRIVE = "drive"


def build_candle_backfill(cfg: dict, dry_run_folder: Path | None = None) -> CandleBackfill:
    folder, archive, calendar = _parts(dry_run_folder)
    nse = NseIndexDays(_nse_library(archive_to=None if dry_run_folder else build_owner_drive_store()))
    from ..rehearsal.candle_wiring import rehearsed_candle_source

    def groww() -> GrowwCandleSource:
        provider = GrowwProvider(cfg)
        return GrowwCandleSource(ReadOnlyGroww(lambda: provider.api), now_ist)  # the only Groww object it holds

    source = rehearsed_candle_source(groww)  # story REH1b: the day's recorded answers when rehearsing, no Groww
    return CandleBackfill(
        source, archive, nse, CandleRvTable(folder), DeferralLog(folder / DEFERRALS), _deriver(calendar), calendar,
        now_ist,
    )  # fmt: skip


def build_candle_verifier() -> CandleRowVerifier:
    """Read-only: no Groww, and an NSE file fetched for the check is never archived."""
    folder, archive, calendar = _parts(None)
    nse = NseIndexDays(_nse_library(archive_to=None))
    return CandleRowVerifier(archive, nse, CandleRvTable(folder), _deriver(calendar), calendar, SERIES_START)


def build_candle_archive() -> CandleArchive:
    """Read-only use of the archived candles (G10's X tool reads the checked 15-minute closes through it)."""
    return _parts(None)[1]


def build_deferral_log(dry_run_folder: Path | None = None) -> DeferralLog:
    return DeferralLog((Path(dry_run_folder) if dry_run_folder else CANDLE_FOLDER) / DEFERRALS)


def _parts(dry_run_folder: Path | None):
    """The table folder, the candle archive and the calendar; a dry run keeps all files under its folder."""
    calendar = build_session_calendar()
    if dry_run_folder:
        folder = Path(dry_run_folder)
        archive = CandleArchive(AreaStore(LocalFolderStore(folder / DRY_RUN_DRIVE), RAW_AREA), folder / MANIFESTS)
        return folder, archive, calendar
    return CANDLE_FOLDER, CandleArchive(_owner_raw_area(), MANIFEST_FOLDER / MANIFESTS), calendar


def _owner_raw_area() -> RawFileStore:
    drive = build_owner_drive()
    if drive is None:
        raise RuntimeError(f"set {', '.join(OWNER_UPLOAD_SETTINGS)} to keep the candles in Drive")
    return AreaStore(drive, RAW_AREA)


def _nse_library(archive_to: RawFileStore | None) -> RawFileLibrary:
    """NSE's index-close files: the owner's Drive first (A10 archived 2017 on), then NSE; a file fetched from NSE is
    archived as A1 does in a live run, never in a dry run."""
    drive = build_owner_drive()
    stores = ([AreaStore(drive, RAW_AREA)] if drive is not None else []) + build_raw_stores()
    return RawFileLibrary(stores, build_nse_source(NseIndexCloseSource), archive_to)


def _deriver(calendar) -> SessionDeriver:
    return SessionDeriver(CandleCloseRv15m(), NseSessionCalendar(calendar, calendar.first).next_open)
