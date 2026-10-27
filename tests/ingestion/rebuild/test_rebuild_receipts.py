"""Story RR1: receipts rebuilt from Drive. Offline: a local folder stands in for Drive."""

from __future__ import annotations

import hashlib
from argparse import Namespace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from fno.ingestion.storage import repair_cli
from fno.ingestion.storage.drive_cache import DriveCache
from fno.ingestion.storage.raw_store import LocalFolderStore
from fno.ingestion.storage.receipt_rebuild import WRITER, ReceiptRebuild
from fno.ingestion.storage.receipts import Receipt, ReceiptFolder

NOW = datetime(2026, 10, 27, 9, 0, tzinfo=UTC)
RUN = "20261027T090000Z-abc123"
CIRCULARS = {f"data/circulars/list/2026/10/part-{n}.csv": f"circular rows {n}\n".encode() for n in range(3)}
FLOWS = {
    "data/flows/history/fii-stats/2026/10/2026-10-26.csv": b"fii rows\n",
    "data/flows/history/participant-volume/2026/10/2026-10-26.csv": b"volume rows\n",
}
PREFIXES = ["data/circulars/list", "data/flows/history"]


def world(tmp_path: Path, files=None):
    drive = LocalFolderStore(tmp_path / "drive")
    for path, data in (files or {**CIRCULARS, **FLOWS}).items():
        drive.put(path, data)
    receipts = ReceiptFolder(tmp_path / "receipts")
    return drive, receipts, ReceiptRebuild(drive, receipts, RUN, clock=lambda: NOW)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_without_receipts_a_sync_stops_and_after_the_rebuild_it_passes_for_both_tables(tmp_path):
    drive, receipts, rebuild = world(tmp_path)
    cache = DriveCache(drive, receipts, root=tmp_path / "cache")
    for prefix in ("data/circulars/list", "data/flows/history/fii-stats", "data/flows/history/participant-volume"):
        assert any("no receipts under it" in p for p in cache.sync(prefix).problems)
    report = rebuild.run(PREFIXES, apply=True)
    assert report.ok and report.counts["written"] == len(CIRCULARS) + len(FLOWS)
    fresh = DriveCache(drive, ReceiptFolder(tmp_path / "receipts"), root=tmp_path / "cache2")
    for prefix in ("data/circulars/list", "data/flows/history/fii-stats", "data/flows/history/participant-volume"):
        assert fresh.sync(prefix).problems == []


def test_every_rebuilt_receipt_carries_the_digest_and_size_of_its_drive_file_and_says_it_is_a_rebuild(tmp_path):
    drive, receipts, rebuild = world(tmp_path)
    rebuild.run(PREFIXES, apply=True)
    for path, data in {**CIRCULARS, **FLOWS}.items():
        found = receipts.read(path)
        assert found == Receipt(path, sha(data), len(data), NOW.isoformat(), WRITER, RUN)
    assert WRITER == "rebuild-receipts"


def test_report_only_is_the_default_and_writes_no_receipt(tmp_path):
    _, receipts, rebuild = world(tmp_path)
    report = rebuild.run(PREFIXES, apply=False)
    assert report.counts["would_write"] == len(CIRCULARS) + len(FLOWS) and report.counts["written"] == 0
    assert not list((tmp_path / "receipts").rglob("*")) and "report only" in report.line()


def test_a_receipt_that_still_matches_is_left_alone_and_one_that_does_not_is_reported_never_replaced(tmp_path):
    drive, receipts, rebuild = world(tmp_path, CIRCULARS)
    good, bad = list(CIRCULARS)[:2]
    receipts.write(Receipt(good, sha(CIRCULARS[good]), len(CIRCULARS[good]), "2026-10-21T00:00:00+00:00", "old", "r0"))
    receipts.write(Receipt(bad, sha(b"what the file used to be"), 5, "2026-10-21T00:00:00+00:00", "old", "r0"))
    report = rebuild.run(["data/circulars/list"], apply=True)
    assert report.counts["already_receipted"] == 1 and report.counts["differs_from_receipt"] == 1
    assert report.counts["written"] == 1 and not report.ok and any(bad in p for p in report.problems)
    assert receipts.read(good).writer == "old" and receipts.read(bad).sha256 == sha(b"what the file used to be")


def test_running_it_twice_changes_nothing_the_second_time(tmp_path):
    _, receipts, rebuild = world(tmp_path)
    rebuild.run(PREFIXES, apply=True)
    second = rebuild.run(PREFIXES, apply=True)
    assert second.counts["already_receipted"] == len(CIRCULARS) + len(FLOWS) and second.counts["written"] == 0


def test_a_file_that_cannot_be_read_is_reported_and_gets_no_receipt(tmp_path):
    drive, receipts, _ = world(tmp_path, CIRCULARS)

    class Flaky(LocalFolderStore):
        def get(self, path):
            raise OSError("Drive said no")

    flaky = Flaky(tmp_path / "drive")
    report = ReceiptRebuild(flaky, receipts, RUN, clock=lambda: NOW).run(["data/circulars/list"], apply=True)
    assert report.counts["unreadable"] == len(CIRCULARS) and report.counts["written"] == 0 and not report.ok
    assert not list((tmp_path / "receipts").rglob("*.sha256")) and "Drive said no" not in " ".join(report.problems)


def test_dot_files_and_files_outside_the_prefixes_are_skipped(tmp_path):
    files = {**CIRCULARS, "data/vix/other.csv": b"x"}
    drive, receipts, _ = world(tmp_path, files)

    class ListsDotFiles(LocalFolderStore):
        def checksums(self, folder):
            found = super().checksums(folder)
            return {**found, ".part-9.csv.part": "0"} if folder == "data/circulars/list/2026/10" else found

        def get(self, path):
            return b"half written" if path.endswith(".part") else super().get(path)

    rebuild = ReceiptRebuild(ListsDotFiles(tmp_path / "drive"), receipts, RUN, clock=lambda: NOW)
    report = rebuild.run(["data/circulars/list"], apply=True)
    assert report.counts["files"] == len(CIRCULARS) and receipts.read("data/vix/other.csv") is None
    assert receipts.read("data/circulars/list/2026/10/.part-9.csv.part") is None


def test_the_command_rebuilds_commits_and_exits_green_and_a_failed_commit_is_red(tmp_path):
    _, _, rebuild = world(tmp_path)
    lines = []

    class Committer:
        def __init__(self, line):
            self.line, self.what = line, None

        def commit(self, what):
            self.what = what
            return self.line

    args = Namespace(prefixes=PREFIXES, apply=True)
    ok = Committer("receipts committed and pushed (5 file(s))")
    assert repair_cli.cmd_rebuild_receipts(args, out=lines.append, rebuild=rebuild, committer=ok) == 0
    assert ok.what.startswith("rebuild-receipts data/circulars/list") and "applied" in lines[0]
    _, _, again = world(tmp_path / "second")
    failed = Committer("receipts NOT committed: push failed: x. Commit receipts/ by hand")
    assert repair_cli.cmd_rebuild_receipts(args, out=lines.append, rebuild=again, committer=failed) == 1


def test_report_only_through_the_command_commits_nothing(tmp_path):
    _, _, rebuild = world(tmp_path)
    boom = type("C", (), {"commit": lambda self, what: pytest.fail("a report-only run must not commit")})()
    args = Namespace(prefixes=PREFIXES, apply=False)
    assert repair_cli.cmd_rebuild_receipts(args, out=lambda line: None, rebuild=rebuild, committer=boom) == 0
