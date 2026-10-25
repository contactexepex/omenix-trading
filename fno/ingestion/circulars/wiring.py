"""Composition root of story A20b: NSE's and SEBI's feeds through a polite session, their freshness rules (NSE's
session calendar), the O9 data store (the owner's Drive, receipts), the verified Drive cache for the circulars already
listed, the receipts and open-problem committers and the #fno-desk alert sender."""

from __future__ import annotations

import os
from functools import partial

from fno.ingestion.circulars.capture import LIST_TABLE, CircularCapture
from fno.ingestion.circulars.episodes import OpenProblems
from fno.ingestion.circulars.feeds import NseCircularApi, SebiCircularList
from fno.ingestion.circulars.freshness import NewestAgeFreshness, PreviousSessionFreshness
from fno.ingestion.circulars.job import CircularsJob
from fno.ingestion.circulars.model import COLUMNS, NSE, SEBI
from fno.ingestion.circulars.relevance import FnoRelevance
from fno.ingestion.composition import build_alert_sender
from fno.ingestion.storage.data_store import new_run_id
from fno.ingestion.storage.data_wiring import DATA_AREA, build_data_store, build_drive_cache, build_receipt_committer
from fno.ingestion.storage.manifest_commit import GitManifestRecorder
from fno.ingestion.storage.part_table import read_parts
from fno.ingestion.storage.wiring import REPOSITORY, build_session_calendar
from fno.shared.alerts.run_location import run_location
from fno.shared.alerts.step_output import StepOutputAlerts, record_posted
from fno.shared.constants import RESEARCH_USER_AGENT
from fno.shared.http_pacing import PacedSession

WRITER = "circulars"
ALERT_STATE_FOLDER = REPOSITORY / "research" / "ops" / "alerts"
ALERT_STATE_FILE = ALERT_STATE_FOLDER / "circulars_open.txt"
ALERT_STATE_MESSAGE = "Circulars: open problems already alerted ({what})"


def listed_circulars(env=os.environ) -> list[dict]:
    """Every row listed so far, from the receipted parts (each verified byte for byte against its receipt)."""
    cache, prefix = build_drive_cache(env), f"{DATA_AREA}/{LIST_TABLE}"
    report = cache.sync(prefix)
    if not report.complete:
        raise RuntimeError("; ".join(report.problems))
    folder = cache.local(prefix)
    return read_parts(folder, COLUMNS) if folder.is_dir() else []


def build_circulars_job(env=os.environ) -> CircularsJob:
    session = PacedSession()
    session.headers["User-Agent"] = RESEARCH_USER_AGENT
    feeds = {NSE: NseCircularApi(session), SEBI: SebiCircularList(session)}
    freshness = {NSE: PreviousSessionFreshness(build_session_calendar()), SEBI: NewestAgeFreshness()}
    capture = CircularCapture(feeds, freshness, FnoRelevance(), build_data_store(WRITER, new_run_id(), env))
    state_committer = GitManifestRecorder(REPOSITORY, ALERT_STATE_FOLDER, message=ALERT_STATE_MESSAGE,
                                          label="open problems")  # fmt: skip
    alerts = StepOutputAlerts(build_alert_sender(), env)  # the workflow's own line speaks only if this did not
    committers, state = (build_receipt_committer(), state_committer), OpenProblems(ALERT_STATE_FILE)
    spoken = partial(record_posted, env)
    return CircularsJob(partial(listed_circulars, env), capture, committers, state, alerts, spoken, run_location(env))
