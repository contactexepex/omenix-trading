"""Story R2: receipts packed one file per run. Every Drive file of a run is proved by its own line in the run's batch
file; the readers (`ReceiptFolder`, `DriveCache.sync`) find it by path, so a batch proves each file as one receipt did.
Offline: a local folder stands in for Drive."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from fno.ingestion.storage.batch_receipts import BATCH_FOLDER, BatchBroken, BatchReceiptWriter
from fno.ingestion.storage.data_store import DataStore
from fno.ingestion.storage.drive_cache import DriveCache
from fno.ingestion.storage.raw_store import LocalFolderStore, RawFileConflict
from fno.ingestion.storage.receipts import Receipt, ReceiptFolder

AREA = "raw"
FILES = {f"news/articles/{n}.json": f"article {n}".encode() for n in range(5)}


RUN = "20261027T120000Z-aaaaaa"


def world(tmp_path: Path, run_id: str = RUN):
    drive = LocalFolderStore(tmp_path / "drive")
    receipts = ReceiptFolder(tmp_path / "receipts")
    store = DataStore(drive, AREA, BatchReceiptWriter(receipts, run_id), "news-promote", run_id)
    return drive, receipts, store


def batch_files(tmp_path: Path) -> list[Path]:
    return sorted((tmp_path / "receipts" / BATCH_FOLDER).rglob("*.tsv"))


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
    assert fresh.batch_problems("raw/news") == []


def test_two_runs_make_two_batch_files_and_never_touch_each_other(tmp_path):
    drive, receipts, _ = world(tmp_path)
    for run in ("20261027T130000Z-bbbbbb", "20261027T140000Z-cccccc"):
        DataStore(drive, AREA, BatchReceiptWriter(receipts, run), "w", run).put(f"x/{run[-1]}", b"a")
    assert [f.name for f in batch_files(tmp_path)] == ["20261027T130000Z-bbbbbb.tsv", "20261027T140000Z-cccccc.tsv"]


def test_the_same_bytes_again_keep_the_first_line_and_different_bytes_are_refused(tmp_path):
    _, receipts, store = world(tmp_path)
    first = store.put("news/a", b"one")
    again = store.put("news/a", b"one")
    assert again == first and len(batch_files(tmp_path)[0].read_text().splitlines()) == 1
    writer = BatchReceiptWriter(receipts, RUN)
    with pytest.raises(RawFileConflict):
        writer.write(receipt("raw/news/a", b"other"))
    assert receipts.read("raw/news/a").sha256 == hashlib.sha256(b"one").hexdigest()


def test_a_different_digest_is_also_refused_against_a_per_file_receipt_and_the_other_way_round(tmp_path):
    receipts = ReceiptFolder(tmp_path / "receipts")
    receipts.write(receipt("raw/news/a", b"one"))
    with pytest.raises(RawFileConflict):
        BatchReceiptWriter(receipts, RUN).write(receipt("raw/news/a", b"other"))
    BatchReceiptWriter(receipts, RUN).write(receipt("raw/news/b", b"two"))
    with pytest.raises(RawFileConflict):
        receipts.write(receipt("raw/news/b", b"other"))


def test_a_path_with_a_tab_or_line_break_is_refused(tmp_path):
    writer = BatchReceiptWriter(ReceiptFolder(tmp_path / "receipts"), RUN)
    for path in ("raw/a\tb", "raw/a\nb", ""):
        with pytest.raises(ValueError):
            writer.write(receipt(path, b"x"))


def put_batch(tmp_path: Path, name: str, text: str) -> None:
    folder = tmp_path / "receipts" / BATCH_FOLDER / "2026" / "10"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_text(text)


def line(path: str, digest: str = "a" * 64, size: str = "1", run: str = "r") -> str:
    return "\t".join([path, digest, size, "2026-10-27T12:00:00+00:00", "w", run]) + "\n"


def test_a_torn_last_line_a_wrong_shape_and_two_digests_are_reported_and_never_read_as_receipts(tmp_path):
    put_batch(tmp_path, "r1.tsv", line("raw/news/a") + "only\tthree\tfields\n" + "raw/news/torn\t" + "c" * 64 + "\t1")
    put_batch(tmp_path, "r2.tsv", line("raw/news/a", "b" * 64, run="r2"))
    receipts = ReceiptFolder(tmp_path / "receipts")
    assert receipts.read("raw/news/a").sha256 == "a" * 64  # the first one is kept
    assert receipts.read("raw/news/torn") is None
    problems = receipts.batch_problems("raw/news")
    assert any("different digest" in p.message and p.path == "raw/news/a" for p in problems)
    assert any(
        p.path == "raw/news/torn" and "not proved" in p.message for p in problems
    )  # the cut-off line names its file
    assert any(p.path is None and "cut short" in p.message for p in problems)
    assert any(p.path is None and "not a whole receipt line" in p.message for p in problems)  # names no file: a warning


@pytest.mark.parametrize(
    "bad",
    [
        line("raw/news/x", digest="zz"),  # a digest that is not 64 hex characters
        line("raw/news/x", size="many"),  # a size that is not a number
        line("../raw/news/x"),  # a path that is not a valid archive path
        line("raw/news/x").replace("\n", "\r\n"),  # a carriage return stays in the last field
        "raw/news/x\t\t\t\t\t\t\t\n",  # too many fields
    ],
)
def test_a_damaged_line_is_a_reported_problem_never_a_crash_and_never_a_receipt(tmp_path, bad):
    put_batch(tmp_path, "r1.tsv", line("raw/news/ok") + bad)
    receipts = ReceiptFolder(tmp_path / "receipts")
    assert receipts.read("raw/news/ok") is not None and receipts.read("raw/news/x") is None
    assert [r.path for r in receipts.under("raw/news")] == ["raw/news/ok"]
    assert receipts.batch_problems("raw/news")


def test_a_batch_file_that_is_not_text_is_a_warning_not_a_crash(tmp_path):
    folder = tmp_path / "receipts" / BATCH_FOLDER / "2026" / "10"
    folder.mkdir(parents=True)
    (folder / "r1.tsv").write_bytes(b"\xff\xfe\x00 not text \x80")
    receipts = ReceiptFolder(tmp_path / "receipts")
    assert receipts.under("raw/news") == [] and [p.path for p in receipts.batch_problems("raw/news")] == [None]


# ---- B1: news damage never reaches an unrelated reader -------------------------------------------------------------


def test_damage_in_a_news_batch_does_not_touch_the_sync_of_an_unrelated_table(tmp_path):
    put_batch(
        tmp_path, "r1.tsv", line("raw/news/a") + "garbage\n" + line("raw/news/b", size="x") + "raw/news/t\t" + "d" * 8
    )
    drive = LocalFolderStore(tmp_path / "drive")
    receipts = ReceiptFolder(tmp_path / "receipts")
    DataStore(drive, "data", receipts, "w", "20261027T120000Z-eeeeee").put("flows/fii/2026.csv", b"x,y\n")
    cache = DriveCache(drive, receipts, root=tmp_path / "cache")
    assert receipts.batch_problems("data/flows/fii") == []
    report = cache.sync("data/flows/fii")
    assert report.complete and report.warnings == [] and report.present + len(report.downloaded) == 1


def test_news_damage_that_names_a_file_fails_a_news_sync_until_the_file_has_a_valid_receipt(tmp_path):
    drive, receipts, store = world(tmp_path, "20261027T120000Z-aaaaaa")
    for path, data in FILES.items():
        store.put(path, data)
    torn_path = f"{AREA}/news/articles/3.json"
    batch = batch_files(tmp_path)[0]
    lines = batch.read_text().splitlines(keepends=True)
    batch.write_text("".join(x for x in lines if torn_path not in x) + torn_path + "\t" + "e" * 10)  # line 3 cut off
    cache = DriveCache(drive, ReceiptFolder(tmp_path / "receipts"), root=tmp_path / "cache")
    report = cache.sync("raw/news/articles")
    assert not report.complete and any(torn_path in p and "not proved" in p for p in report.problems)
    # the way out: the next run saves the same file again, its valid line settles the cut-off one
    again = DataStore(
        drive, AREA, BatchReceiptWriter(cache.receipts, "20261027T130000Z-bbbbbb"), "w", "20261027T130000Z-bbbbbb"
    )
    again.put("news/articles/3.json", FILES["news/articles/3.json"])
    fresh = DriveCache(drive, ReceiptFolder(tmp_path / "receipts"), root=tmp_path / "cache2")
    assert fresh.sync("raw/news/articles").problems == []


def test_damage_that_names_no_file_is_a_warning_and_the_news_sync_still_completes(tmp_path):
    drive, receipts, store = world(tmp_path)
    for path, data in FILES.items():
        store.put(path, data)
    batch = batch_files(tmp_path)[0]
    batch.write_text(batch.read_text() + "garbage line with no tabs\n")
    cache = DriveCache(drive, ReceiptFolder(tmp_path / "receipts"), root=tmp_path / "cache")
    report = cache.sync("raw/news/articles")
    assert report.complete and len(report.warnings) == 1 and report.present + len(report.downloaded) == len(FILES)


# ---- B2: a short write never glues two receipt lines ---------------------------------------------------------------


def test_a_write_that_returns_short_is_finished_not_left_half_written(tmp_path, monkeypatch):
    import os as os_module

    real = os_module.write

    def two_bytes_at_a_time(descriptor, data):
        return real(descriptor, bytes(data)[:2])

    monkeypatch.setattr("fno.ingestion.storage.batch_receipts.os.write", two_bytes_at_a_time)
    _, receipts, store = world(tmp_path)
    store.put("news/a", b"a")
    store.put("news/b", b"b")
    fresh = ReceiptFolder(tmp_path / "receipts")
    assert fresh.read("raw/news/a") is not None and fresh.read("raw/news/b") is not None
    assert fresh.batch_problems("raw/news") == []


def test_a_write_that_fails_halfway_makes_the_next_append_refuse_instead_of_gluing_onto_it(tmp_path, monkeypatch):
    import os as os_module

    real, calls = os_module.write, []

    def fails_after_a_few_bytes(descriptor, data):
        calls.append(1)
        if len(calls) == 1:
            real(descriptor, bytes(data)[:10])
            raise OSError("disk full")
        return real(descriptor, data)

    monkeypatch.setattr("fno.ingestion.storage.batch_receipts.os.write", fails_after_a_few_bytes)
    _, receipts, store = world(tmp_path)
    with pytest.raises(OSError):
        store.put("news/a", b"a")
    half = batch_files(tmp_path)[0].read_bytes()
    with pytest.raises(BatchBroken):
        store.put("news/b", b"b")  # refuses; the half line is not extended
    assert batch_files(tmp_path)[0].read_bytes() == half


def test_a_write_that_makes_no_progress_is_an_error_not_an_endless_loop(tmp_path, monkeypatch):
    calls = []

    def writes_nothing(descriptor, data):
        calls.append(1)
        assert len(calls) < 50, "looped"
        return 0

    monkeypatch.setattr("fno.ingestion.storage.batch_receipts.os.write", writes_nothing)
    _, _, store = world(tmp_path)
    with pytest.raises(BatchBroken):
        store.put("news/a", b"a")


def test_a_batch_file_that_does_not_end_in_a_line_break_takes_no_more_lines(tmp_path):
    put_batch(tmp_path, "20261027T120000Z-aaaaaa.tsv", line("raw/news/a") + "raw/news/torn\tabc")
    _, receipts, store = world(tmp_path)
    with pytest.raises(BatchBroken):
        store.put("news/new", b"x")


# ---- precedence: a per-file receipt is read first, a different batch digest is reported ---------------------------


def test_a_per_file_receipt_wins_and_a_different_batch_digest_for_the_same_path_is_reported(tmp_path):
    put_batch(tmp_path, "r1.tsv", line("raw/news/a", "b" * 64))
    receipts = ReceiptFolder(tmp_path / "receipts")
    per_file = receipts.file_for("raw/news/a")  # a state the writers cannot make (they refuse): made by hand
    per_file.parent.mkdir(parents=True)
    per_file.write_text(receipt("raw/news/a", b"one").to_text())
    assert receipts.read("raw/news/a").sha256 == hashlib.sha256(b"one").hexdigest()
    assert [r.sha256 for r in receipts.under("raw/news")] == [hashlib.sha256(b"one").hexdigest()]
    assert any(p.path == "raw/news/a" and "per-file" in p.message for p in receipts.batch_problems("raw/news"))


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


def test_the_batch_file_is_sharded_by_the_month_of_its_run_id(tmp_path):
    _, _, store = world(tmp_path, "20261103T010000Z-dddddd")
    store.put("news/a", b"a")
    assert [f.relative_to(tmp_path / "receipts" / BATCH_FOLDER).as_posix() for f in batch_files(tmp_path)] == [
        "2026/11/20261103T010000Z-dddddd.tsv"
    ]


@pytest.mark.parametrize("run_id", ["r1", "2026", "20261327T000000Z-x", "abcdefgh", ""])
def test_a_run_id_without_its_date_is_refused_when_the_writer_is_made_before_any_drive_write(tmp_path, run_id):
    with pytest.raises(ValueError, match="starts with its UTC date"):
        BatchReceiptWriter(ReceiptFolder(tmp_path / "receipts"), run_id)


# ---- fail closed: a Record file with no valid receipt line is reported, never passed ---------------------------------


def test_a_file_whose_batch_line_was_dropped_is_listed_as_unreceipted(tmp_path):
    _, cache = synced(tmp_path)
    batch = batch_files(tmp_path)[0]
    kept = [line for line in batch.read_text().splitlines(keepends=True) if "/2.json" not in line]
    assert len(kept) == len(FILES) - 1
    batch.write_text("".join(kept))
    fresh = DriveCache(cache.drive, ReceiptFolder(tmp_path / "receipts"), root=tmp_path / "cache2")
    assert fresh.unreceipted("raw/news/articles") == ["raw/news/articles/2.json"]


def test_a_file_whose_last_batch_line_is_torn_is_reported_as_unproved_and_as_unreceipted(tmp_path):
    _, cache = synced(tmp_path)
    batch = batch_files(tmp_path)[0]
    lines = batch.read_text().splitlines(keepends=True)
    torn = lines[-1].split("\t")[0] + "\t" + lines[-1].split("\t")[1][:20]  # cut off in the middle of the digest
    batch.write_text("".join(lines[:-1]) + torn)
    fresh = DriveCache(cache.drive, ReceiptFolder(tmp_path / "receipts"), root=tmp_path / "cache2")
    path = lines[-1].split("\t")[0]
    assert any(p.startswith(f"{path}: ") and "not proved" in p for p in fresh.sync("raw/news/articles").problems)
    assert fresh.unreceipted("raw/news/articles") == [path]  # torn is missing, never a valid receipt


def test_nothing_is_unreceipted_when_every_file_has_its_line_and_per_file_receipts_count_too(tmp_path):
    drive, cache = synced(tmp_path)
    assert cache.unreceipted("raw/news/articles") == []
    drive.put("raw/news/articles/extra.json", b"x")
    cache.receipts.write(receipt("raw/news/articles/extra.json", b"x"))
    assert cache.unreceipted("raw/news/articles") == []
    drive.put("raw/news/articles/.hidden.part", b"y")  # a dot-file is not data
    assert cache.unreceipted("raw/news/articles") == []


def test_the_cache_command_lists_unreceipted_files_only_when_asked(tmp_path, monkeypatch):
    from argparse import Namespace

    from fno.ingestion.storage import cache_cli, data_wiring

    drive, cache = synced(tmp_path)
    drive.put("raw/news/articles/loose.json", b"no receipt for this")
    monkeypatch.setattr(data_wiring, "build_drive_cache", lambda: cache)
    quiet, asked = [], []
    assert cache_cli.cmd_cache_sync(Namespace(prefix="raw/news/articles", unreceipted=False), out=quiet.append) == 0
    code = cache_cli.cmd_cache_sync(Namespace(prefix="raw/news/articles", unreceipted=True), out=asked.append)
    assert code == 1 and any("loose.json" in line and "no receipt" in line for line in asked)
    assert not any("loose.json" in line for line in quiet)


def test_a_cut_off_line_is_settled_by_a_per_file_receipt_as_written_by_the_repair_command(tmp_path):
    """Judge 61 F3: `data-repair receipt --apply` writes a per-file receipt; that must clear the problem, or a news
    sync would stay red until someone edited a committed batch file."""
    drive, receipts, store = world(tmp_path)
    store.put("news/articles/1.json", FILES["news/articles/1.json"])
    torn_path = f"{AREA}/news/articles/b.json"
    drive.put(torn_path, b"b")
    batch = batch_files(tmp_path)[0]
    batch.write_text(
        batch.read_text() + torn_path + "\t" + "f" * 12
    )  # a hand-made torn tail (the guard cuts real ones)
    cache = DriveCache(drive, ReceiptFolder(tmp_path / "receipts"), root=tmp_path / "cache")
    assert any(torn_path in p for p in cache.sync("raw/news/articles").problems)
    cache.receipts.write(receipt(torn_path, b"b"))  # exactly what ReceiptRepair.write does: a per-file receipt
    fresh = DriveCache(drive, ReceiptFolder(tmp_path / "receipts"), root=tmp_path / "cache2")
    assert fresh.sync("raw/news/articles").problems == []
