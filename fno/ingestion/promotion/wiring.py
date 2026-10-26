"""Composition root of the staging -> promotion pipeline (docs/PIPELINE_DESIGN.md, Phase 1): the only place that picks
the concrete stores. The stager gets an AreaStore on `staging`, so it cannot reach the Record (`raw`); the gate gets
the Record store (Drive `raw` area with its manifest rows) and is the only thing wired to write it from staged files."""

from __future__ import annotations

import os

from fno.ingestion.promotion.checks import FreshnessCheck, PromotionCheck, SchemaCheck
from fno.ingestion.promotion.gate import PromotionGate
from fno.ingestion.promotion.runs import PromotionRun, Stager
from fno.ingestion.promotion.staging import StagingArea
from fno.ingestion.storage.raw_store import AreaStore
from fno.ingestion.storage.source_lists import LIBRARIAN_DATASETS
from fno.ingestion.storage.wiring import (
    OWNER_UPLOAD_SETTINGS,
    build_file_exceptions,
    build_nse_source,
    build_owner_drive,
    build_owner_drive_store,
    build_session_calendar,
    coverage_datasets,
)

STAGING_AREA = "staging"
NSE_TAG = "nse"  # the source tag of NSE's archive: the authoritative source of every dataset staged so far
DEFAULT_MAX_LAG_DAYS = 7  # a daily run promotes files fetched within a week of their session (owner to confirm)
NEEDS_DRIVE = "set {settings} to use the staging area"

PROMOTABLE_DATASETS = tuple(sorted(LIBRARIAN_DATASETS))  # the dated NSE datasets the librarian already archives


def build_staging_area(env=os.environ) -> StagingArea:
    drive = build_owner_drive(env)
    if drive is None:
        raise RuntimeError(NEEDS_DRIVE.format(settings=", ".join(OWNER_UPLOAD_SETTINGS)))
    return StagingArea(AreaStore(drive, STAGING_AREA))


def build_stager(dataset: str) -> Stager:
    """The dataset's NSE source into Staging (and the calendar's sessions); writes nothing else."""
    source = build_nse_source(LIBRARIAN_DATASETS[dataset])
    return Stager(source, build_staging_area(), NSE_TAG, build_session_calendar(), build_file_exceptions())


def build_promotion_run(dataset: str, max_lag_days: int | None = DEFAULT_MAX_LAG_DAYS, env=os.environ) -> PromotionRun:
    """Staging -> checks -> the Record, for one dataset. `max_lag_days=None` is for a back-fill."""
    source_type = LIBRARIAN_DATASETS[dataset]
    record = build_owner_drive_store(env)
    if record is None:
        raise RuntimeError(NEEDS_DRIVE.format(settings=", ".join(OWNER_UPLOAD_SETTINGS)))
    validate = next(d.validate for d in coverage_datasets() if d.source is source_type)
    checks: list[PromotionCheck] = [FreshnessCheck(max_lag_days), SchemaCheck(validate)]
    gate = PromotionGate(build_staging_area(env), record, NSE_TAG, checks)
    return PromotionRun(gate, source_type, build_session_calendar(), build_file_exceptions())
