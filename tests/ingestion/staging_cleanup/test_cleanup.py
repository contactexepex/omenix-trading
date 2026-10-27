"""Story S1: the staging cleanup. Offline: a local folder stands in for Drive, a recording fake for the trash."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from fno.ingestion.promotion.staging import StagingArea
from fno.ingestion.staging_cleanup.cleanup import MAX_AGE, StagingCleanup
from fno.ingestion.staging_cleanup.proof import KeepForever, NseCopyProof
from fno.ingestion.staging_cleanup.trash import StagingTrash
from fno.ingestion.storage.raw_store import AreaStore, LocalFolderStore

NOW = datetime(2026, 10, 27, 12, 0, tzinfo=UTC)
PATH = "nse/derivatives/participant-oi/2026/10/f.csv"
OLD = NOW - MAX_AGE - timedelta(seconds=1)
EXACTLY_7_DAYS = NOW - MAX_AGE
YOUNG = NOW - timedelta(days=6, hours=23)


class Revisions:
    def __init__(self, *held: tuple[str, str]):
        self.held = set(held)

    def holds(self, path: str, sha256: str) -> bool:
        return (path, sha256) in self.held


class Trash(StagingTrash):
    def __init__(self, fail: bool = False, gone: bool = False):
        self.calls, self.fail, self.gone = [], fail, gone

    def trash(self, source: str, archive_path: str, stamp: str) -> bool:
        self.calls.append((source, archive_path, stamp))
        if self.fail:
            raise OSError("Drive said no")
        return not self.gone


class World:
    def __init__(self, tmp_path: Path):
        drive = LocalFolderStore(tmp_path / "drive")
        self.staging = StagingArea(AreaStore(drive, "staging"))
        self.record = AreaStore(drive, "raw")

    def stage(self, data: bytes, at: datetime, source: str = "nse", path: str = PATH) -> None:
        self.staging.stage(source, path, data, at)

    def cleanup(self, trash=None, revisions=None, limit=500, proofs=None):
        proofs = proofs or {"nse": NseCopyProof(self.record, revisions or Revisions()), "news": KeepForever()}
        return StagingCleanup(self.staging, proofs, trash, clock=lambda: NOW, limit=limit)


def stamp(at: datetime) -> str:
    return at.strftime("%Y%m%dT%H%M%SZ")


def test_an_old_copy_the_record_holds_exactly_is_trashed(tmp_path):
    w = World(tmp_path)
    w.stage(b"good", OLD)
    w.record.put(PATH, b"good")
    trash = Trash()
    report = w.cleanup(trash).run(["nse"])
    assert trash.calls == [("nse", PATH, stamp(OLD))] and report.counts["trashed"] == 1 and report.ok


def test_report_only_is_the_default_and_calls_nothing(tmp_path):
    w = World(tmp_path)
    w.stage(b"good", OLD)
    w.record.put(PATH, b"good")
    report = w.cleanup(None).run(["nse"])
    assert report.counts["would_trash"] == 1 and report.counts["trashed"] == 0 and not report.apply
    assert "report only" in report.line()


def test_a_copy_the_record_does_not_hold_is_never_trashed(tmp_path):
    w = World(tmp_path)
    w.stage(b"rejected by the gate, never recorded", OLD)
    trash = Trash()
    report = w.cleanup(trash).run(["nse"])
    assert trash.calls == [] and report.counts["unproven"] == 1


def test_a_copy_whose_bytes_differ_from_the_record_is_kept_unless_the_revisions_hold_it(tmp_path):
    w = World(tmp_path)
    w.stage(b"later version", OLD)
    w.record.put(PATH, b"first version")
    trash = Trash()
    assert w.cleanup(trash).run(["nse"]).counts["unproven"] == 1 and trash.calls == []
    digest = hashlib.sha256(b"later version").hexdigest()
    report = w.cleanup(trash, Revisions((PATH, digest))).run(["nse"])
    assert report.counts["trashed"] == 1 and len(trash.calls) == 1


def test_a_copy_younger_than_seven_days_or_exactly_seven_is_kept(tmp_path):
    w = World(tmp_path)
    w.record.put(PATH, b"good")
    for at in (YOUNG, EXACTLY_7_DAYS):
        w.stage(b"good", at, path=f"{PATH}.{stamp(at)}")
        w.record.put(f"{PATH}.{stamp(at)}", b"good")
    trash = Trash()
    report = w.cleanup(trash).run(["nse"])
    assert trash.calls == [] and report.counts["young"] == 2 and report.counts["scanned"] == 0


def test_a_source_without_a_rule_is_never_trashed(tmp_path):
    w = World(tmp_path)
    w.stage(b"poll", OLD, source="news", path="feed-01/2026/10/01/poll")
    w.stage(b"other", OLD, source="other", path="x/y")
    trash = Trash()
    report = w.cleanup(trash).run(["news", "other"])
    assert trash.calls == [] and report.counts["unproven"] == 1 and report.counts["no_rule"] == 1


def test_a_failed_trash_is_counted_and_makes_the_run_not_ok(tmp_path):
    w = World(tmp_path)
    w.stage(b"good", OLD)
    w.record.put(PATH, b"good")
    report = w.cleanup(Trash(fail=True)).run(["nse"])
    assert report.counts["failed"] == 1 and report.counts["trashed"] == 0 and not report.ok


def test_a_copy_already_gone_is_counted_as_such(tmp_path):
    w = World(tmp_path)
    w.stage(b"good", OLD)
    w.record.put(PATH, b"good")
    assert w.cleanup(Trash(gone=True)).run(["nse"]).counts["already_gone"] == 1


def test_a_record_that_cannot_be_read_keeps_the_copy(tmp_path):
    w = World(tmp_path)
    w.stage(b"good", OLD)

    class Down(AreaStore):
        def get(self, path):
            raise OSError("Drive down")

    proof = NseCopyProof(Down(LocalFolderStore(tmp_path / "x"), "raw"), Revisions())
    trash = Trash()
    report = w.cleanup(trash, proofs={"nse": proof}).run(["nse"])
    assert trash.calls == [] and report.counts["unproven"] == 1


def test_the_limit_bounds_the_copies_examined(tmp_path):
    w = World(tmp_path)
    for n in range(5):
        path = f"{PATH}.{n}"
        w.stage(b"good", OLD, path=path)
        w.record.put(path, b"good")
    trash = Trash()
    report = w.cleanup(trash, limit=2).run(["nse"])
    assert len(trash.calls) == 2 and report.counts["limit_reached"] == 1


def test_the_report_holds_counts_only(tmp_path):
    w = World(tmp_path)
    w.stage(b"secret-looking-bytes", OLD)
    w.record.put(PATH, b"secret-looking-bytes")
    line = w.cleanup(Trash()).run(["nse"]).line()
    assert "secret-looking" not in line and "participant-oi" not in line and PATH not in line


def test_every_old_staged_copy_of_one_path_is_judged_on_its_own(tmp_path):
    w = World(tmp_path)
    w.stage(b"first", OLD - timedelta(days=2))
    w.stage(b"second", OLD)
    w.record.put(PATH, b"first")
    trash = Trash()
    report = w.cleanup(trash).run(["nse"])
    assert [c[2] for c in trash.calls] == [stamp(OLD - timedelta(days=2))]
    assert report.counts["trashed"] == 1 and report.counts["unproven"] == 1


@pytest.mark.parametrize("sources", [["nse"], ["nse", "nse"]])
def test_the_walk_finds_staged_paths_at_any_depth(tmp_path, sources):
    w = World(tmp_path)
    for path in ("a.csv", "x/y/z/deep.csv"):
        w.stage(b"good", OLD, path=path)
        w.record.put(path, b"good")
    assert w.cleanup(None).run(sources[:1]).counts["would_trash"] == 2
