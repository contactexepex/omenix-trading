"""Composition root of story A15, the India VIX full history: the only place that picks its concrete parts. NSE's
month files through the shared polite session, the owner's Drive raw area with its manifest rows (A9), A11's revisions
area and index, the table and its checks in Drive with receipts (O9b's pilot), NSE's session calendar and the
committed index-close closes (A10) for the overlap check."""

from __future__ import annotations

import os

from ..models import now_ist
from ..research_data.panel_store import WARMUP_FILE
from ..storage import wiring as storage
from ..storage.data_wiring import build_data_store, build_drive_cache
from ..storage.manifest_folder import FingerprintingStore, ManifestFolder
from ..storage.raw_store import AreaStore, RawFileStore
from ..storage.receipted_rows import ReceiptedRowLog, ReceiptedSnapshots
from ..storage.revisions import RevisionArchive, RevisionIndex
from .check_files import CHECK_FILES, VixCheckFiles, committed_vix_closes
from .librarian import VixHistoryLibrarian
from .month_file import NseVixJsonReader
from .source import NseVixHistorySource
from .sweep import VixRevisionSweep
from .table import VixDailyTable
from .table_builder import VixTableBuilder
from .verify import VixTableVerifier

WRITER = "vix-history"
DRIVE_TABLE, DRIVE_CHECKS = "vix/india_vix_daily", "vix/checks/{stem}"  # inside Drive's `data` area
REFERENCE_CLOSES = storage.PANEL_FOLDER / WARMUP_FILE  # India VIX closes from NSE's daily index-close files (A10)
SOURCES = (NseVixHistorySource,)
DRIVE_SETTINGS_MISSING = f"set {', '.join(storage.OWNER_UPLOAD_SETTINGS)} to use the India VIX archive in Drive"


def _owner_drive(env=os.environ):
    drive = storage.build_owner_drive(env)
    if drive is None:
        raise RuntimeError(DRIVE_SETTINGS_MISSING)
    return drive


def _fingerprints(manifests: ManifestFolder) -> dict:
    """Month -> SHA-256 of its archived file, from the dataset's manifest."""
    return {f.day: f.sha256 for f in manifests.read(NseVixHistorySource)}


def _source() -> NseVixHistorySource:
    return storage.build_nse_source(NseVixHistorySource)


def build_vix_librarian(raw: RawFileStore, log=print) -> VixHistoryLibrarian:
    """NSE's month files into the raw area, each saved file getting its manifest row (A9)."""
    manifests = storage.build_manifest_folder()
    store = FingerprintingStore(raw, manifests, SOURCES)
    path_for = NseVixHistorySource.path_for
    return VixHistoryLibrarian(store, _source(), path_for, NseVixJsonReader(), _fingerprints(manifests), log)


def _table_log() -> ReceiptedRowLog:
    return ReceiptedRowLog(build_data_store(WRITER), build_drive_cache(), DRIVE_TABLE)


def _check_reports() -> dict[str, ReceiptedSnapshots]:
    store, cache = build_data_store(WRITER), build_drive_cache()
    folders = {name: DRIVE_CHECKS.format(stem=name.rsplit(".", 1)[0]) for name in CHECK_FILES}
    return {name: ReceiptedSnapshots(store, cache, folder) for name, folder in folders.items()}


def build_vix_table() -> VixDailyTable:
    return VixDailyTable(_table_log())


def build_vix_table_builder(raw: RawFileStore) -> VixTableBuilder:
    path_for, reader = NseVixHistorySource.path_for, NseVixJsonReader()
    return VixTableBuilder(raw, path_for, reader, build_vix_table(), now_ist, _committed_fingerprints)


def _committed_fingerprints() -> dict:
    """The manifest rows as committed when the extension starts (after the fill has added its own)."""
    return _fingerprints(storage.build_manifest_folder())


def build_vix_checks(reports=None) -> VixCheckFiles:
    """`reports`: the check reports by file name (default: Drive snapshots with receipts)."""
    calendar = storage.build_session_calendar()
    return VixCheckFiles(reports or _check_reports(), calendar, calendar.first,
                         lambda: committed_vix_closes(REFERENCE_CLOSES))  # fmt: skip


def build_vix_verifier(raw: RawFileStore) -> VixTableVerifier:
    """The table recomputed from the archived month files, checked against their manifest rows."""
    manifest = _fingerprints(storage.build_manifest_folder())
    return VixTableVerifier(raw, NseVixHistorySource.path_for, NseVixJsonReader(), manifest)


def build_vix_raw_area(env=os.environ) -> RawFileStore:
    """The owner's Drive raw area, where the month files are archived and read back."""
    return AreaStore(_owner_drive(env), storage.RAW_AREA)


def build_vix_revision_sweep(env=os.environ) -> VixRevisionSweep:
    """NSE read again, later versions kept by A11's revision archive with their own index file."""
    drive = _owner_drive(env)
    raw, revisions = AreaStore(drive, storage.RAW_AREA), AreaStore(drive, storage.REVISIONS_AREA)
    index = RevisionIndex(storage.REVISION_INDEX_FOLDER, SOURCES)
    manifests = storage.build_manifest_folder()
    archive = RevisionArchive(raw, revisions, index, manifests)
    path_for, reader = NseVixHistorySource.path_for, NseVixJsonReader()
    return VixRevisionSweep(_source(), archive, raw, path_for, reader, _fingerprints(manifests))
