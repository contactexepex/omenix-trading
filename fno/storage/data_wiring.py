"""Composition root of story O9's data store: the owner's Drive project folder (written and read as the owner, one
credential), the checkout's `receipts/` tree, the A16f committer for the receipts and the local Drive cache. Apart
from `wiring.py`, which is at the size limit."""

from __future__ import annotations

import os

from .data_store import DataStore, new_run_id
from .drive_cache import DriveCache
from .manifest_commit import GitManifestRecorder
from .raw_store import RawFileStore
from .receipts import ReceiptFolder
from .wiring import OWNER_UPLOAD_SETTINGS, REPOSITORY, build_owner_drive

# The Drive area of every data file, the checkout's receipts tree and the git-ignored local cache (O9)
DATA_AREA, RECEIPTS_FOLDER, DRIVE_CACHE_FOLDER = "data", "receipts", "work/drive-cache"
RECEIPTS_MESSAGE = "Receipts: SHA-256 of Drive data files ({what})"
RECEIPTS_LABEL = "receipts"


def receipt_folder() -> ReceiptFolder:
    return ReceiptFolder(REPOSITORY / RECEIPTS_FOLDER)


def _owner_drive(env=os.environ) -> RawFileStore:
    drive = build_owner_drive(env)
    if drive is None:
        raise RuntimeError(f"set {', '.join(OWNER_UPLOAD_SETTINGS)} to use the Drive data store")
    return drive


def build_data_store(writer: str, run_id: str | None = None, env=os.environ) -> DataStore:
    """The write path for one run of `writer` (a job or command name)."""
    return DataStore(_owner_drive(env), DATA_AREA, receipt_folder(), writer, run_id or new_run_id())


def build_receipt_committer() -> GitManifestRecorder:
    """Commits and pushes `receipts/` to origin main whatever branch the container is on (A16f)."""
    return GitManifestRecorder(REPOSITORY, REPOSITORY / RECEIPTS_FOLDER, message=RECEIPTS_MESSAGE,
                               label=RECEIPTS_LABEL)  # fmt: skip


def build_drive_cache(env=os.environ) -> DriveCache:
    return DriveCache(_owner_drive(env), receipt_folder(), REPOSITORY / DRIVE_CACHE_FOLDER)
