"""Composition root of story A4h: NSE's public index list (no Groww), O9's Drive data store and the checkout's
receipts, the archived index-close files, A7's calendar, the #fno-desk sender and the IST clock."""

from __future__ import annotations

import os
import time

from fno.ingestion.close_read.confirm import Confirmer
from fno.ingestion.close_read.constants import DATA_AREA, ROOT, WRITER
from fno.ingestion.close_read.official import ArchivedIndexCloses
from fno.ingestion.close_read.reader import CloseReader
from fno.ingestion.close_read.source import NseIndexList
from fno.ingestion.close_read.store import DriveClosesStore
from fno.ingestion.composition import build_alert_sender
from fno.ingestion.providers.public import PublicData
from fno.ingestion.storage.data_wiring import RECEIPTS_FOLDER, RECEIPTS_MESSAGE, build_data_store, receipt_folder
from fno.ingestion.storage.manifest_commit import GitManifestRecorder
from fno.ingestion.storage.wiring import (
    REPOSITORY,
    build_owner_drive,
    build_session_calendar,
    build_stored_index_close_files,
)
from fno.shared.alerts.reported import ReportedAlerts
from fno.shared.models import now_ist

NO_DRIVE = "set the four FNO_GDRIVE_* owner settings to use A4h's Drive data store"
RECEIPTS_LABEL = "close-read receipts"


def build_receipts_committer() -> GitManifestRecorder:
    """A hand or evening run's own commit of A4h's receipts only (O1's steps commit them through their pathspec):
    uncommitted, a fresh checkout would not see them, read again and meet Drive's write-once file (judge 447)."""
    folder = REPOSITORY / RECEIPTS_FOLDER / DATA_AREA / ROOT
    return GitManifestRecorder(REPOSITORY, folder, message=RECEIPTS_MESSAGE, label=RECEIPTS_LABEL)


def build_close_reader(env=os.environ) -> CloseReader:
    drive = build_owner_drive(env)
    if drive is None:
        raise RuntimeError(NO_DRIVE)
    store = DriveClosesStore(drive, build_data_store(WRITER, env=env), receipt_folder())
    calendar = build_session_calendar()
    alerts = ReportedAlerts(build_alert_sender())  # an unsent alert is printed with its text (O2)
    confirmer = Confirmer(store, ArchivedIndexCloses(build_stored_index_close_files()), calendar, alerts, now=now_ist)
    source = NseIndexList(PublicData().nse_json)
    return CloseReader(source, store, confirmer, calendar, now_ist, time.sleep)
