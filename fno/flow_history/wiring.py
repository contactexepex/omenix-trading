"""Composition root of story A23: the two NSE datasets' value readers, the owner's Drive (raw archive, data store and
verified cache), A8's write-time sweep with its log in the repository, A7's calendar, the manifests, the committers
and the #fno-desk alert sender."""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

from ..alerts.step_output import StepOutputAlerts
from ..composition import build_alert_sender
from ..constants import RESEARCH_USER_AGENT
from ..http_pacing import PacedSession
from ..research_data.write_sweep import LastWriteSweep, read_sweeps
from ..storage.data_wiring import (
    DATA_AREA,
    RECEIPTS_FOLDER,
    RECEIPTS_LABEL,
    RECEIPTS_MESSAGE,
    build_data_store,
    build_drive_cache,
    receipt_folder,
)
from ..storage.manifest_commit import GitManifestRecorder
from ..storage.part_table import PartTable, read_parts
from ..storage.source_lists import dataset_name
from ..storage.trading_days import next_trading_day
from ..storage.wiring import (
    OWNER_UPLOAD_SETTINGS,
    REPOSITORY,
    build_manifest_folder,
    build_nse_source,
    build_owner_drive_store,
    build_session_calendar,
)
from .nsdl_backfill import NsdlArchiveForm, NsdlBackfill
from .table import COLUMNS, TABLE, FlowTableJob
from .values import FiiDerivativeStatsValues, FlowValues, ParticipantVolumeValues

WRITER = "flow-history"
EVIDENCE_FOLDER = REPOSITORY / "research" / "data" / "flow_history"
WRITE_TIMES_FILE = "{name}_write_times.csv"
EVIDENCE_MESSAGE = "A23 flow history: NSE write times ({what})"
VALUES = {dataset_name(v.source): v for v in (ParticipantVolumeValues(), FiiDerivativeStatsValues())}
NSDL_TABLE = "nsdl-fpi"  # private Drive only, never in the repository or a public place (owner, 50a79a43)


def write_time_log(name: str) -> Path:
    return EVIDENCE_FOLDER / WRITE_TIMES_FILE.format(name=name)


def archived_days(name: str) -> list[date]:
    return [row.day for row in build_manifest_folder().read(VALUES[name].source)]


def entered_sessions(name: str, env=os.environ) -> set[date]:
    """The sessions already in the dataset's table, from its receipted parts (each verified against its receipt)."""
    cache, prefix = build_drive_cache(env), f"{DATA_AREA}/{TABLE.format(name=name)}"
    report = cache.sync(prefix)
    if not report.complete:
        raise RuntimeError("; ".join(report.problems))
    folder = cache.local(prefix)
    return {date.fromisoformat(row["session"]) for row in read_parts(folder, COLUMNS)} if folder.is_dir() else set()


def build_flow_table_job(name: str, env=os.environ) -> FlowTableJob:
    values: FlowValues = VALUES[name]
    raw = build_owner_drive_store(env)
    if raw is None:
        raise RuntimeError(f"set {', '.join(OWNER_UPLOAD_SETTINGS)} to read the archive")
    calendar, log = build_session_calendar(), write_time_log(name)
    sweep = LastWriteSweep(build_nse_source(values.source), values.source.path_for, log)
    table = PartTable(build_data_store(WRITER, env=env), TABLE.format(name=name), COLUMNS)
    return FlowTableJob(values, raw, sweep, lambda: read_sweeps(log), lambda day: next_trading_day(calendar, day),
                        table, date.today)  # fmt: skip


def build_committers() -> tuple[GitManifestRecorder, GitManifestRecorder]:
    """The write-time log first (it may have changed upstream), then the receipts (new files never block a pull)."""
    evidence_path = EVIDENCE_FOLDER.relative_to(REPOSITORY).as_posix()
    evidence = GitManifestRecorder(REPOSITORY, EVIDENCE_FOLDER, message=EVIDENCE_MESSAGE, label="write times",
                                   run_paths=(f"{RECEIPTS_FOLDER}/",))  # fmt: skip
    receipts = GitManifestRecorder(REPOSITORY, REPOSITORY / RECEIPTS_FOLDER, message=RECEIPTS_MESSAGE,
                                   label=RECEIPTS_LABEL, run_paths=(f"{evidence_path}/",))  # fmt: skip
    return evidence, receipts


def build_alerts(env=os.environ) -> StepOutputAlerts:
    return StepOutputAlerts(build_alert_sender(), env)  # the workflow's own line speaks only if this did not


def build_nsdl_backfill(env=os.environ) -> NsdlBackfill:
    session = PacedSession()
    session.headers["User-Agent"] = RESEARCH_USER_AGENT
    store, calendar = build_data_store(WRITER, env=env), build_session_calendar()
    table = PartTable(store, TABLE.format(name=NSDL_TABLE), COLUMNS)
    return NsdlBackfill(NsdlArchiveForm(session), store, receipt_folder(), table,
                        lambda day: next_trading_day(calendar, day))  # fmt: skip
