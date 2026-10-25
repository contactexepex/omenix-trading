"""Composition root of story DR1's records: per dataset, its rules, where its versions come from and the shadow's
comparison; the owner's Drive project folder (read by path), the checkout's receipts and its `receipts/records/` tree
with a committer of that tree only. First dataset: A4h's closes, in shadow (A4h's raw answers as the versions).

The certifier only reads: the official index-close files come from O9's one reader builder,
`build_stored_index_close_files()` (the stores only, the owner's Drive raw area included, never NSE, never a Drive
write; with no store at all it raises NoReadableStore, which the certifier turns into a loud failure)."""

from __future__ import annotations

import os

from ..close_read.official import ArchivedIndexCloses
from ..storage.data_wiring import receipt_folder
from ..storage.manifest_commit import GitManifestRecorder
from ..storage.wiring import (
    OWNER_UPLOAD_SETTINGS,
    REPOSITORY,
    build_owner_drive,
    build_session_calendar,
    build_stored_index_close_files,
)
from .certifier import Certifier
from .closes import DATASET as CLOSES
from .closes import A4hRecordComparison, ClosesRules, a4h_raw_paths
from .constants import RECORDS_FOLDER, RECORDS_LABEL, RECORDS_MESSAGE
from .publisher import GitRecordPublisher
from .reader import RecordReader
from .record_folder import RecordFolder
from .staging import ReceiptedFiles

DATASETS = (CLOSES,)


def _drive(env=os.environ):
    drive = build_owner_drive(env)
    if drive is None:
        raise RuntimeError(f"set {', '.join(OWNER_UPLOAD_SETTINGS)} to read the Drive data folder")
    return drive


def build_record_folder(commit: bool) -> RecordFolder:
    folder = REPOSITORY / RECORDS_FOLDER
    if not commit:
        return RecordFolder(folder)
    committer = GitManifestRecorder(REPOSITORY, folder, message=RECORDS_MESSAGE, label=RECORDS_LABEL)
    return RecordFolder(folder, GitRecordPublisher(REPOSITORY, committer))


def build_certifier(dataset: str, commit: bool, env=os.environ) -> Certifier:
    if dataset != CLOSES:
        raise ValueError(f"no certification rules for {dataset!r}; known: {', '.join(DATASETS)}")
    drive = _drive(env)
    rules = ClosesRules(
        ArchivedIndexCloses(build_stored_index_close_files()), build_session_calendar().previous_session
    )
    versions = ReceiptedFiles(receipt_folder(), a4h_raw_paths)
    return Certifier(rules, versions, drive, build_record_folder(commit), A4hRecordComparison(drive))


def build_alerts():
    """#fno-desk through the bot token; an alert Slack did not take is printed with its text (O1's ReportedAlerts)."""
    from ..composition import build_alert_sender
    from ..daily.alerts import ReportedAlerts

    return ReportedAlerts(build_alert_sender())


def build_record_reader(env=os.environ) -> RecordReader:
    return RecordReader(build_record_folder(commit=False), _drive(env))
