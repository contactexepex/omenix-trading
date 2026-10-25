"""Composition root of story A20a's job: NSE's sources and the owner's Drive through the raw-data wiring, the session
calendar, the manifest committer and the #fno-desk alert sender."""

from __future__ import annotations

import os
from datetime import date

from ..alerts.run_location import run_location
from ..alerts.step_output import StepOutputAlerts
from ..composition import build_alert_sender
from ..storage.snapshot_source import FoBanListSource, FoLotSizeSource
from ..storage.source_lists import dataset_name
from ..storage.trading_days import is_trading_day
from ..storage.wiring import (
    OWNER_UPLOAD_SETTINGS,
    build_manifest_recorder,
    build_owner_drive_store,
    build_session_calendar,
    build_snapshot_taker,
)
from .job import FoMastersJob, Step, ban_list_step, taken


def archived_ban_list(day: date) -> bool:
    """Whether the owner's Drive holds a ban list filed under the session `day`."""
    store = build_owner_drive_store()
    if store is None:
        raise RuntimeError(f"set {', '.join(OWNER_UPLOAD_SETTINGS)} to read Drive")
    return store.get(FoBanListSource.path_for(day)) is not None


def build_fo_masters_job(env=os.environ) -> FoMastersJob:
    calendar = build_session_calendar()
    ban, lots = (dataset_name(s) for s in (FoBanListSource, FoLotSizeSource))
    take_ban = ban_list_step(lambda day: build_snapshot_taker(ban).take(day), archived_ban_list,
                             lambda day: is_trading_day(calendar, day))  # fmt: skip
    steps = (
        Step("ban list", take_ban, every_day=True),  # NSE writes the next session's list the evening before
        Step("lot sizes", lambda day: taken(build_snapshot_taker(lots).take(day))),
    )
    alerts = StepOutputAlerts(build_alert_sender(), env)  # the workflow's own line speaks only if this did not
    return FoMastersJob(calendar, steps, build_manifest_recorder(), alerts, run_location(env))
