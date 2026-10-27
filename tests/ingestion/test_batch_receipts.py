"""Story R2: receipts packed one file per run. Every Drive file of a run is proved by its own line in the run's batch
file; the readers (`ReceiptFolder`, `DriveCache.sync`) find it by path, so a batch proves each file as one receipt did.
Offline: a local folder stands in for Drive."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from fno.ingestion.storage.batch_receipts import BATCH_FOLDER, BatchReceiptWriter
from fno.ingestion.storage.data_store import DataStore
from fno.ingestion.storage.drive_cache import DriveCache
from fno.ingestion.storage.raw_store import LocalFolderStore, RawFileConflict
from fno.ingestion.storage.receipts import Receipt, ReceiptFolder

AREA = "raw"
FILES = {f"news/articles/{n}.json": f"article {n}".encode() for n in range(5)}


def world(tmp_path: Path, run_id: str = "20261027T120000Z-aaaaaa"):
    drive = LocalFolderStore(tmp_path / "drive")
    receipts = ReceiptFolder(tmp_path / "receipts")
    store = DataStore(drive, AREA, BatchReceiptWriter(receipts), "news-promote", run_id)
    return drive, receipts, store


def batch_files(tmp_path: Path) -> list[Path]:
    return sorted((tmp_path / "receipts" / BATCH_FOLDER).glob("*.tsv"))


def receipt(path: str, data: bytes, run_id: str = "r1") -> Receipt:
    return Receipt(path, hashlib.sha256(data).hexdigest(), len(data), "2026-10-27T12:00:00+00:00", "w", run_id)


def test_every_file_of_a_run_is_proved_by_its_own_line_found_by_path(tmp_path):
    _, receipts, store = world(tmp_path)
    for path, data in FILES.items():
        store.put(path, data)
    assert len(batch_files(tmp_path)) == 1 and not list((tmp_path / "receipts").rglob("*.sha256"))
    fresh = ReceiptFolder(tmp_path / "receipts")  # a new process reads the committed files
    for path, data in FILES.items():
        found = fresh.read(f"{AREA}/{path}")
        assert found is not None and found.sha256 == hashlib.sha256(data).hexdigest() and found.size == len(data)
    assert [r.path for r in fresh.under("raw/news/articles")] == sorted(f"{AREA}/{p}" for p in FILES)
    assert fresh.batch_problems() == []


def test_two_runs_make_two_batch_files_and_never_touch_each_other(tmp_path):
    drive, receipts, _ = world(tmp_path)
    DataStore(drive, AREA, BatchReceiptWriter(receipts), "w", "20261027T130000Z-bbbbbb").put("x/a", b"a")
    DataStore(drive, AREA, BatchReceiptWriter(receipts), "w", "20261027T140000Z-cccccc").put("x/b", b"b")
    assert [f.name for f in batch_files(tmp_path)] == ["20261027T130000Z-bbbbbb.tsv", "20261027T140000Z-cccccc.tsv"]


def test_the_same_bytes_again_keep_the_first_line_and_different_bytes_are_refused(tmp_path):
    _, receipts, store = world(tmp_path)
    first = store.put("news/a", b"one")
    again = store.put("news/a", b"one")
    assert again == first and len(batch_files(tmp_path)[0].read_text().splitlines()) == 1
    writer = BatchReceiptWriter(receipts)
    with pytest.raises(RawFileConflict):
        writer.write(receipt("raw/news/a", b"other"))
    assert receipts.read("raw/news/a").sha256 == hashlib.sha256(b"one").hexdigest()


def test_a_different_digest_is_also_refused_against_a_per_file_receipt_and_the_other_way_round(tmp_path):
    receipts = ReceiptFolder(tmp_path / "receipts")
    receipts.write(receipt("raw/news/a", b"one"))
    with pytest.raises(RawFileConflict):
        BatchReceiptWriter(receipts).write(receipt("raw/news/a", b"other"))
    BatchReceiptWriter(receipts).write(receipt("raw/news/b", b"two"))
    with pytest.raises(RawFileConflict):
        receipts.write(receipt("raw/news/b", b"other"))


def test_a_path_with_a_tab_or_line_break_is_refused(tmp_path):
    writer = BatchReceiptWriter(ReceiptFolder(tmp_path / "receipts"))
    for path in ("raw/a\tb", "raw/a\nb", ""):
        with pytest.raises(ValueError):
            writer.write(receipt(path, b"x"))


def test_a_torn_last_line_a_wrong_shape_and_two_digests_are_reported_and_never_read_as_receipts(tmp_path):
    folder = tmp_path / "receipts" / BATCH_FOLDER
    folder.mkdir(parents=True)
    good = "\t".join(["raw/n/a", "a" * 64, "1", "2026-10-27T12:00:00+00:00", "w", "r1"]) + "\n"
    other = "\t".join(["raw/n/a", "b" * 64, "1", "2026-10-27T12:00:00+00:00", "w", "r2"]) + "\n"
    (folder / "r1.tsv").write_text(good + "only\tthree\tfields\n" + "raw/n/torn\t" + "c" * 64 + "\t1")
    (folder / "r2.tsv").write_text(other)
    receipts = ReceiptFolder(tmp_path / "receipts")
    assert receipts.read("raw/n/a").sha256 == "a" * 64  # the first one is kept
    assert receipts.read("raw/n/torn") is None
    problems = receipts.batch_problems()
    assert len(problems) == 3 and any("cut short" in p for p in problems) and any("not 6 fields" in p for p in problems)
    assert any("different digest" in p for p in problems)


# ---- the verified cache over a batch-receipted prefix ------------------------------------------------------------


def synced(tmp_path):
    drive, receipts, store = world(tmp_path)
    for path, data in FILES.items():
        store.put(path, data)
    return drive, DriveCache(drive, ReceiptFolder(tmp_path / "receipts"), root=tmp_path / "cache")


def test_the_cache_brings_every_batch_receipted_file_to_disk_verified(tmp_path):
    _, cache = synced(tmp_path)
    report = cache.sync("raw/news/articles")
    assert report.problems == [] and len(report.downloaded) == len(FILES)


def test_a_drive_file_changed_behind_its_batch_receipt_is_found(tmp_path):
    drive, cache = synced(tmp_path)
    (tmp_path / "drive" / "raw" / "news" / "articles" / "2.json").write_bytes(b"tampered")
    report = cache.sync("raw/news/articles")
    assert len(report.problems) == 1 and "raw/news/articles/2.json" in report.problems[0]
    assert len(report.downloaded) == len(FILES) - 1


def test_a_drive_file_missing_behind_its_batch_receipt_is_found(tmp_path):
    drive, cache = synced(tmp_path)
    (tmp_path / "drive" / "raw" / "news" / "articles" / "3.json").unlink()
    report = cache.sync("raw/news/articles")
    assert len(report.problems) == 1 and "raw/news/articles/3.json" in report.problems[0]


def test_a_torn_batch_shows_up_in_the_cache_report(tmp_path):
    _, cache = synced(tmp_path)
    batch = batch_files(tmp_path)[0]
    batch.write_text(batch.read_text() + "raw/news/articles/9.json\t" + "d" * 64)
    fresh = DriveCache(cache.drive, ReceiptFolder(tmp_path / "receipts"), root=tmp_path / "cache2")  # a new process
    assert any("cut short" in p for p in fresh.sync("raw/news/articles").problems)
