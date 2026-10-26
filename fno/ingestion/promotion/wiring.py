"""Composition root of the staging -> promotion pipeline (docs/PIPELINE_DESIGN.md, Phase 1): the only place that picks
the concrete stores. The stager gets an AreaStore on `staging`, so it cannot reach the Record (`raw`); the gate gets
the Record store (Drive `raw` area with its manifest rows) and is the only thing wired to write it from staged files."""

from __future__ import annotations

import os

from fno.ingestion.promotion.checks import ContentDayCheck, FreshnessCheck, PromotionCheck, SchemaCheck
from fno.ingestion.promotion.datasets import PROMOTABLE
from fno.ingestion.promotion.gate import PromotionGate
from fno.ingestion.promotion.runs import PromotionRun, Stager
from fno.ingestion.promotion.staging import StagingArea
from fno.ingestion.storage.raw_store import AreaStore
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
NEEDS_DRIVE = "set {settings} to use the staging area"

PROMOTABLE_DATASETS = tuple(sorted(PROMOTABLE))


def build_staging_area(env=os.environ) -> StagingArea:
    drive = build_owner_drive(env)
    if drive is None:
        raise RuntimeError(NEEDS_DRIVE.format(settings=", ".join(OWNER_UPLOAD_SETTINGS)))
    return StagingArea(AreaStore(drive, STAGING_AREA))


def build_stager(dataset: str) -> Stager:
    """The dataset's NSE source into Staging (and the calendar's sessions); writes nothing else."""
    source = build_nse_source(PROMOTABLE[dataset].source)
    return Stager(source, build_staging_area(), NSE_TAG, build_session_calendar(), build_file_exceptions())


def checks_for(dataset: str, validate, max_lag_days: int | None = None) -> list[PromotionCheck]:
    """The dataset's content check, its identity check where its content check does not read a date, and the owner's
    numeric window only when `promotion.max_lag_days` is set (none by default: open decision 1)."""
    checks: list[PromotionCheck] = [SchemaCheck(validate)]
    if PROMOTABLE[dataset].content_days is not None:
        checks.append(ContentDayCheck(PROMOTABLE[dataset].content_days))
    if max_lag_days is not None:
        checks.append(FreshnessCheck(max_lag_days))
    return checks


def build_promotion_run(dataset: str, max_lag_days: int | None = None, env=os.environ) -> PromotionRun:
    """Staging -> checks -> the Record, for one dataset."""
    source_type = PROMOTABLE[dataset].source
    record = build_owner_drive_store(env)
    if record is None:
        raise RuntimeError(NEEDS_DRIVE.format(settings=", ".join(OWNER_UPLOAD_SETTINGS)))
    validate = next(d.validate for d in coverage_datasets() if d.source is source_type)
    gate = PromotionGate(build_staging_area(env), record, NSE_TAG, checks_for(dataset, validate, max_lag_days))
    return PromotionRun(gate, source_type, build_session_calendar(), build_file_exceptions())
