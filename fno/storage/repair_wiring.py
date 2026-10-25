"""Composition root of story DR1-0's Drive repairs: the owner's Drive project folder seen item by item, the checkout's
receipts and the path-based store that reads back after a merge. Apart from `data_wiring.py` (O9's data store)."""

from __future__ import annotations

import os

from .data_wiring import receipt_folder
from .drive_items import DriveItems
from .folder_merge import FolderMerge
from .receipt_repair import ReceiptRepair
from .wiring import OWNER_UPLOAD_SETTINGS, build_owner_drive


def _owner_drive(env=os.environ):
    drive = build_owner_drive(env)
    if drive is None:
        raise RuntimeError(f"set {', '.join(OWNER_UPLOAD_SETTINGS)} to repair the Drive data folder")
    return drive


def build_folder_merge(env=os.environ) -> FolderMerge:
    drive = _owner_drive(env)
    return FolderMerge(DriveItems(drive), receipt_folder(), build_owner_drive(env))


def build_receipt_repair(env=os.environ) -> ReceiptRepair:
    return ReceiptRepair(DriveItems(_owner_drive(env)), receipt_folder())
