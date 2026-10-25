"""Composition root of story A4h: NSE's public index list (no Groww), O9's Drive data store and the checkout's
receipts, the archived index-close files, A7's calendar, the #fno-desk sender and the IST clock."""

from __future__ import annotations

import os
import time

from ..composition import build_alert_sender
from ..daily.alerts import ReportedAlerts
from ..models import now_ist
from ..providers.public import PublicData
from ..storage.data_wiring import RECEIPTS_FOLDER, RECEIPTS_MESSAGE, build_data_store, receipt_folder
from ..storage.manifest_commit import GitManifestRecorder
from ..storage.wiring import REPOSITORY, build_owner_drive, build_session_calendar, build_stored_index_close_files
from .confirm import Confirmer
from .constants import DATA_AREA, ROOT, WRITER
from .official import ArchivedIndexCloses
from .reader import CloseReader
from .source import NseIndexList
from .store import DriveClosesStore

NO_DRIVE = "set the four FNO_GDRIVE_* owner settings to use A4h's Drive data store"
RECEIPTS_LABEL = "close-read receipts"


def receipt_pathspecs() -> tuple[str, ...]:
    """The receipts of A4h's Drive files only, never the shared `receipts/` root (O1's step commits these)."""
    return (f"receipts/{DATA_AREA}/{ROOT}/",)


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
    from ..rehearsal.close_wiring import rehearsed_close_list

    source = rehearsed_close_list(NseIndexList(PublicData().nse_json), drive)  # REH1b: the recorded answers
    return CloseReader(source, store, confirmer, calendar, now_ist, time.sleep)
