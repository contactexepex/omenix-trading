"""Composition root of story A13 (G1 protocol v3): the daily NIFTY panel job, apart from O6's shared
`fno/pipeline/wiring.py` so that v3's freeze can pin exactly this wiring and leave O6's other jobs free to change
(judge 64; the same reason `fno/forecast/baseline_wiring.py` is apart from G1 v1's `wiring.py`). It reads only Drive's
raw area (the first archived version of each input); `drive_files` is also used by O6's daily index-close job.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from datetime import date
from functools import cache

from ..composition import build_alert_sender
from ..constants import PANEL_FORMAT_LEGACY, PANEL_FORMAT_UDIFF, PANEL_INDEX_CLOSE
from ..models import now_ist
from ..research_data.nifty_panel import DailyFiles, NiftyPanelBuilder
from ..research_data.panel_append import PanelAppender
from ..storage import wiring as storage
from ..storage.raw_source import NseArchiveSource, NseDailyFoSource, NseIndexCloseSource, NseLegacyFoSource
from ..storage.raw_store import AreaStore, RawFileStore
from ..storage.revisions import RevisionIndex
from .panel_days import PanelDayJob

DRIVE_SETTINGS_MISSING = f"set {', '.join(storage.OWNER_UPLOAD_SETTINGS)} to read the archived files in Drive"


def drive_files(label: str, source: type[NseArchiveSource], store: RawFileStore) -> DailyFiles:
    """A dataset's daily files as held in Drive (never fetched from NSE here)."""
    get = cache(lambda path: store.get(path))  # the input check and the builder read the same file once
    return DailyFiles(
        label, source.dataset, source.first_day, source.last_day,
        lambda day: (source.filename_for(day), get(source.path_for(day))),
    )  # fmt: skip


VERSIONED_SOURCES = {"fo": NseDailyFoSource, "index-close": NseIndexCloseSource}


def require_v3_frozen() -> None:
    """G1 v3's freeze, this job's section only (a change to G4's question-5 files never stops the panel job)."""
    from ..config import ROOT
    from ..freeze_sections import PANEL_DAYS, require_section_frozen
    from ..research_engine.ledger import Git

    require_section_frozen(ROOT, Git(ROOT).head(), PANEL_DAYS)


def first_archived_inputs(drive: RawFileStore) -> tuple[list[DailyFiles], DailyFiles]:
    """A3's inputs as first archived in Drive's raw area (A11 keeps later versions apart; they are never read here)."""
    raw = AreaStore(drive, storage.RAW_AREA)
    fo_files = [
        drive_files(PANEL_FORMAT_UDIFF, NseDailyFoSource, raw),
        drive_files(PANEL_FORMAT_LEGACY, NseLegacyFoSource, raw),
    ]
    return fo_files, drive_files(PANEL_INDEX_CLOSE, NseIndexCloseSource, raw)


def later_versions(index: RevisionIndex) -> Callable[[date, str], list[dict]]:
    """The later A11 versions known now of a day's input (recorded in the day's provenance, never used)."""

    def lookup(day: date, label: str) -> list[dict]:
        found = index.for_path(VERSIONED_SOURCES[label].path_for(day))
        return [{"sha256": r.sha256, "available_from": r.available_from.isoformat()} for r in found]

    return lookup


def build_panel_day_job(env=os.environ) -> PanelDayJob:
    """Story A13: A3's builder on the first archived F&O and index-close files in Drive, appended to the panel folder,
    only under G1 protocol v3's freeze."""
    drive = storage.build_owner_drive(env)
    if drive is None:
        raise RuntimeError(DRIVE_SETTINGS_MISSING)
    fo_files, index_files = first_archived_inputs(drive)
    calendar = storage.build_session_calendar()
    builder = NiftyPanelBuilder(fo_files, index_files, calendar, storage.build_file_exceptions())
    lookup = later_versions(storage.build_revision_index())
    return PanelDayJob(builder, PanelAppender(storage.PANEL_FOLDER), calendar, require_v3_frozen, lookup,
                       build_alert_sender(), now_ist)  # fmt: skip
