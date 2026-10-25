"""Composition root of the fetch-then-trigger pipeline (story O6): the only place that picks the concrete trigger,
Drive store, batch finder and alert sender, and which routine each download job fires. A new job is one line in JOBS;
a new routine is one line in ROUTINES (its two repository secrets); another store or trigger is one new class here."""

from __future__ import annotations

import os
from datetime import timedelta

from ..alerts.step_output import StepOutputAlerts
from ..composition import build_alert_sender
from ..constants import (
    DERIVED_AREA,
    ENV_ROUTINE_DRY_RUN_TOKEN,
    ENV_ROUTINE_DRY_RUN_TRIGGER_ID,
    PANEL_INDEX_CLOSE,
    PIPELINE_AREA,
    ROUTINE_DRY_RUN,
)
from ..models import now_ist
from ..storage import wiring as storage
from ..storage.raw_source import (
    NseArchiveSource,
    NseIndexCloseSource,
    ParticipantOiSource,
)
from ..storage.raw_store import AreaStore, RawFileStore
from .batches import ManifestBatches
from .dispatcher import BatchDispatcher
from .dry_run import DryRunRoutine
from .index_closes import IndexCloseAppender
from .panel_wiring import drive_files
from .records import PipelineRecords
from .run import PipelineRun
from .run_summary import RunSummaryStore
from .trigger import RoutineFireTrigger, RoutineTrigger, UnconfiguredTrigger

ROUTINES = {ROUTINE_DRY_RUN: (ENV_ROUTINE_DRY_RUN_TRIGGER_ID, ENV_ROUTINE_DRY_RUN_TOKEN)}  # name -> its two secrets
JOBS: dict[str, tuple[str, type[NseArchiveSource]]] = {
    "participant-oi-release": (ROUTINE_DRY_RUN, ParticipantOiSource),  # A8's daily check, then A9's upload
    "participant-oi-sweep": (ROUTINE_DRY_RUN, ParticipantOiSource),  # A8's monthly sweep: republished files (A11)
}  # job -> (routine it fires, dataset it downloads)
POINTER_DATASETS = frozenset(source.dataset for _, source in JOBS.values())  # what a routine accepts in a pointer
DRIVE_SETTINGS_MISSING = f"set {', '.join(storage.OWNER_UPLOAD_SETTINGS)} to use the pipeline's Drive areas"


def build_trigger(routine: str, env=os.environ) -> RoutineTrigger:
    """The routine's `/fire` trigger from its two secrets, or one that fails loudly naming the missing ones."""
    names = ROUTINES[routine]
    trigger_id, token = (env.get(name) for name in names)
    if not (trigger_id and token):
        return UnconfiguredTrigger(routine, tuple(n for n in names if not env.get(n)))
    return RoutineFireTrigger(routine, trigger_id, token)


def _project_drive(env=os.environ) -> RawFileStore:
    drive = storage.build_owner_drive(env)
    if drive is None:
        raise RuntimeError(DRIVE_SETTINGS_MISSING)
    return drive


def build_pipeline_run(job: str, days: int, env=os.environ) -> PipelineRun:
    """A job's batches of the last `days` days, fired to its routine, summarised in Drive's pipeline area."""
    routine, source = JOBS[job]
    since = now_ist().date() - timedelta(days=days)
    finder = ManifestBatches(
        source,
        storage.build_manifest_folder(),
        storage.build_revision_index(),
        since,
        (storage.RAW_AREA, storage.REVISIONS_AREA),
    )
    pipeline = AreaStore(_project_drive(env), PIPELINE_AREA)
    dispatcher = BatchDispatcher(PipelineRecords(pipeline, now_ist), build_trigger(routine, env))
    return PipelineRun(job, finder, dispatcher, RunSummaryStore(pipeline), build_alert_sender(), now_ist)


def build_dry_run_routine(env=os.environ) -> DryRunRoutine:
    """The example routine: reads the whole project folder, writes only the derived and pipeline areas."""
    drive = _project_drive(env)
    records = PipelineRecords(AreaStore(drive, PIPELINE_AREA), now_ist)
    return DryRunRoutine(drive, AreaStore(drive, DERIVED_AREA), records, ROUTINE_DRY_RUN)


def build_index_close_appender(env=os.environ) -> IndexCloseAppender:
    """The daily index-close job: NSE's index-close files as archived in the owner's Drive (never fetched here, so a
    row is the first archived version), appended to the panel folder's warm-up closes."""
    files = drive_files(PANEL_INDEX_CLOSE, NseIndexCloseSource, AreaStore(_project_drive(env), storage.RAW_AREA))
    alerts = StepOutputAlerts(build_alert_sender())  # its workflow's failure line speaks only if this did not (O8c)
    return IndexCloseAppender(files, storage.build_session_calendar(), storage.PANEL_FOLDER, alerts)
