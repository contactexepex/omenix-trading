"""The verified Drive cache and the write-once data store (``fno/ingestion/storage/drive_cache.py`` and
``data_store.py``), exercised entirely OFFLINE.

These are the ``-m data`` tests. The plan's ``data`` marker means "reads data from the verified cache". Here that
cache is built from a TEMP fixture under ``tmp_path``: a ``LocalFolderStore`` stands in for Google Drive, a
``DataStore`` writes bytes + SHA-256 receipt into it, and ``DriveCache.sync`` brings every receipted file to disk
with its bytes checked against the receipt -- exactly the production path, with no real Drive, Slack, Groww or NSE
call. This keeps the ``data-checks.yml`` ``pytest -m data`` step meaningful offline.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from fno.ingestion.storage.data_store import DataStore, new_run_id
from fno.ingestion.storage.drive_cache import DriveCache
from fno.ingestion.storage.raw_store import LocalFolderStore, RawFileConflict
from fno.ingestion.storage.receipts import Receipt, ReceiptFolder

pytestmark = pytest.mark.data

AREA = "data"
REL_PATH = "research/forecast/sample.csv"
FIXTURE_BYTES = b"session,close\n2026-10-12,22100.00\n2026-10-09,22000.50\n"


def _seed(tmp_path: Path):
    """Build a temp 'verified cache': a local-folder Drive, a receipt folder, a data store and a cache reader."""
    drive = LocalFolderStore(tmp_path / "drive")
    receipts = ReceiptFolder(tmp_path / "receipts")
    store = DataStore(drive, AREA, receipts, writer="stage3-test", run_id=new_run_id())
    cache = DriveCache(drive, receipts, root=tmp_path / "cache")
    return drive, receipts, store, cache


def test_put_writes_drive_and_receipt(tmp_path: Path) -> None:
    drive, receipts, store, _ = _seed(tmp_path)
    receipt = store.put(REL_PATH, FIXTURE_BYTES)
    assert receipt.sha256 == hashlib.sha256(FIXTURE_BYTES).hexdigest()
    assert drive.get(f"{AREA}/{REL_PATH}") == FIXTURE_BYTES
    assert receipts.read(f"{AREA}/{REL_PATH}") is not None


def test_sync_verifies_and_downloads_then_is_present(tmp_path: Path) -> None:
    _, _, store, cache = _seed(tmp_path)
    store.put(REL_PATH, FIXTURE_BYTES)
    report = cache.sync(f"{AREA}/research")
    assert report.complete
    assert report.downloaded == [f"{AREA}/{REL_PATH}"]
    on_disk = cache.local(f"{AREA}/{REL_PATH}")
    assert on_disk.read_bytes() == FIXTURE_BYTES  # the fixture round-tripped through the verified cache

    again = cache.sync(f"{AREA}/research")  # second sync: already present, nothing re-downloaded
    assert again.complete and again.present == 1 and again.downloaded == []


def test_sync_reports_missing_drive_file(tmp_path: Path) -> None:
    drive, _, store, cache = _seed(tmp_path)
    store.put(REL_PATH, FIXTURE_BYTES)
    (drive.folder / AREA / "research" / "forecast" / "sample.csv").unlink()  # Drive lost the file
    report = cache.sync(f"{AREA}/research")
    assert not report.complete
    assert any("not returned by Drive" in problem for problem in report.problems)


def test_sync_reports_damaged_bytes(tmp_path: Path) -> None:
    drive = LocalFolderStore(tmp_path / "drive")
    receipts = ReceiptFolder(tmp_path / "receipts")
    drive.put(f"{AREA}/{REL_PATH}", FIXTURE_BYTES)
    # A receipt whose SHA-256 does not match the Drive bytes: the cache must refuse the file.
    receipts.write(Receipt(f"{AREA}/{REL_PATH}", hashlib.sha256(b"other").hexdigest(), 5,
                           "2026-10-12T10:00:00+00:00", "test", "run"))  # fmt: skip
    report = DriveCache(drive, receipts, root=tmp_path / "cache").sync(f"{AREA}/research")
    assert not report.complete
    assert any("do not match the receipt" in problem for problem in report.problems)


def test_sync_wrong_prefix_is_a_problem_not_empty_success(tmp_path: Path) -> None:
    _, _, store, cache = _seed(tmp_path)
    store.put(REL_PATH, FIXTURE_BYTES)
    report = cache.sync(f"{AREA}/no/such/folder")
    assert not report.complete
    assert any("no receipts under it" in problem for problem in report.problems)


def test_data_store_rejects_same_path_different_bytes(tmp_path: Path) -> None:
    _, _, store, _ = _seed(tmp_path)
    store.put(REL_PATH, FIXTURE_BYTES)
    store.put(REL_PATH, FIXTURE_BYTES)  # same bytes: idempotent
    with pytest.raises(RawFileConflict):
        store.put(REL_PATH, b"different content entirely")
