"""Composition root of `fno/school/dashcam/` (story MS-P1c): O9's data store, the verified Drive cache and the A16f
receipt committer, wired into the school's `DashcamStore`, seal checker and replay reader."""

import os
from pathlib import Path

from ...storage.data_wiring import (
    DATA_AREA,
    RECEIPTS_FOLDER,
    REPOSITORY,
    build_data_store,
    build_drive_cache,
    receipt_folder,
)
from ...storage.manifest_commit import GitManifestRecorder
from ...storage.receipt_publisher import GitReceiptPublisher, ReceiptPublisher
from .counts import PublicCountsFile
from .names import SCHOOL_AREA
from .reader import VerifiedDriveReader
from .replay import ReplayReader
from .seals import SealChecker
from .store import DriveDashcamStore

WRITER = "school dashcam"
RECEIPTS_MESSAGE = "Receipts: school dashcam files ({what})"
RECEIPTS_LABEL = "dashcam receipts"


def build_dashcam(run_id: str | None = None, env=os.environ,
                  publisher: ReceiptPublisher | None = None) -> DriveDashcamStore:  # fmt: skip
    """The real store: Drive through the owner's credential, receipts committed to the checkout's `main`.
    `publisher`: another way to the receipts (a fleet step's reads go through its run's, which never fetches)."""
    data = build_data_store(WRITER, run_id, env)
    return DriveDashcamStore(data, publisher or build_receipt_publisher(),
                             VerifiedDriveReader(build_drive_cache(env), DATA_AREA))  # fmt: skip


def build_receipt_publisher() -> GitReceiptPublisher:
    """The school's receipts, committed and pushed to the checkout's `main`."""
    folder = REPOSITORY / RECEIPTS_FOLDER / DATA_AREA / SCHOOL_AREA  # only the school's receipts
    recorder = GitManifestRecorder(REPOSITORY, folder, message=RECEIPTS_MESSAGE, label=RECEIPTS_LABEL)
    return GitReceiptPublisher(recorder, receipt_folder(), REPOSITORY)


def build_seal_checker(store: DriveDashcamStore) -> SealChecker:
    return SealChecker(store.publisher, store.data.area)


def build_replay_reader(store: DriveDashcamStore) -> ReplayReader:
    return ReplayReader(store)


def build_public_counts(root: Path = REPOSITORY) -> PublicCountsFile:
    return PublicCountsFile(root)
