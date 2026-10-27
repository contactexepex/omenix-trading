"""P2d: "as known at T", the composition root on a fake Drive, privacy of every output, the command, the workflow."""

from __future__ import annotations

import ast
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path

import yaml

from fno.ingestion.cli import build_parser
from fno.ingestion.news import cli as news_cli
from fno.ingestion.news.cluster_record import wiring
from fno.ingestion.news.cluster_record.article_source import ArticleSource
from fno.ingestion.news.cluster_record.cluster_file import cluster_path
from fno.ingestion.news.cluster_record.reader import ClusterReader
from fno.ingestion.news.record.manifest import NewsManifest
from fno.ingestion.storage.batch_receipts import BatchReceiptWriter
from fno.ingestion.storage.raw_store import AreaStore, LocalFolderStore
from fno.ingestion.storage.receipts import ReceiptFolder
from tests.ingestion.news.cluster_record.helpers import AS_OF, HEADLINE, OTHER, World, item
from tests.ingestion.news.fakes import MARK_HEADLINE, MARK_HOST, MARK_PATH, MARK_QUERY

ROOT = Path(__file__).resolve().parents[4]


# ---- the reader: "as known at T" (design N10) ---------------------------------------------------------------------


def test_a_story_older_than_the_newest_files_window_is_reached_through_an_earlier_file(tmp_path):
    world = World(tmp_path)
    world.add(item(HEADLINE, "https://pub.example/a/1", 8))
    world.cluster()  # window end 27 Oct 12:00 covers the story
    later = AS_OF + timedelta(days=3)
    world.cluster(later)  # a later file whose window no longer covers it
    reader = ClusterReader(AreaStore(world.drive, "raw"), world.version())
    story = datetime(2026, 10, 27, 8, 0, tzinfo=UTC)
    assert reader.as_known_at(later, story).window_end == AS_OF
    assert reader.as_known_at(later, later - timedelta(hours=1)).window_end == later
    assert reader.as_known_at(AS_OF - timedelta(hours=1), story) is None  # nothing was known before the first file


def test_the_reader_and_the_article_source_cannot_write(tmp_path):
    class NoWrites(LocalFolderStore):
        def put(self, path, data):
            raise AssertionError("a reader must never write")

    world = World(tmp_path)
    world.add(item(HEADLINE, "https://pub.example/a/1"))
    world.cluster()
    ro = NoWrites(world.drive.folder)
    record = AreaStore(ro, "raw")
    assert ClusterReader(record, world.version()).as_known_at(AS_OF, AS_OF - timedelta(hours=2))
    assert ArticleSource(record, NewsManifest(world.record.manifest_folder)).candidates(AS_OF).articles


# ---- the composition root --------------------------------------------------------------------------------------


class RecordingDrive(LocalFolderStore):
    def __init__(self, folder):
        super().__init__(folder)
        self.writes, self.reads = [], []

    def put(self, path, data):
        self.writes.append(path)
        super().put(path, data)

    def get(self, path):
        self.reads.append(path)
        return super().get(path)


def test_the_wired_run_writes_only_the_cluster_area_and_reads_only_the_record(tmp_path, monkeypatch):
    world = World(tmp_path)
    world.add(item(HEADLINE, "https://pub.example/a/1"), item(OTHER, "https://pub.example/b/1"))
    drive = RecordingDrive(world.drive.folder)
    monkeypatch.setattr(wiring, "build_owner_drive", lambda env=None: drive)
    monkeypatch.setattr(
        wiring,
        "batch_receipt_writer",
        lambda run_id: BatchReceiptWriter(ReceiptFolder(tmp_path / "repo" / "receipts"), run_id),
    )
    monkeypatch.setattr(wiring, "POLL_LOG_FOLDER", world.record.manifest_folder)
    report = wiring.build_news_cluster().run(AS_OF)
    assert report.ok and report.counts["clusters"] == 2
    assert drive.writes and all(p.startswith("raw/news/clusters/") for p in drive.writes)
    assert all(p.startswith(("raw/news/articles/", "raw/news/clusters/")) for p in drive.reads)
    again = wiring.build_news_cluster().run(AS_OF)
    assert again.outcome == "no_op" and len(drive.writes) == 1  # a second process reads the file back
    receipts = tmp_path / "repo" / "receipts"  # the cluster file is receipted by a line of the run's batch file
    assert len(list((receipts / "_batches").rglob("*.tsv"))) == 1  # the articles of the test world have per-file ones
    assert not list((receipts / "raw" / "news" / "clusters").rglob("*.sha256"))
    assert [r.path for r in ReceiptFolder(receipts).under("raw/news/clusters")] == drive.writes


# ---- privacy: the master test, through P2b1, P2b2, P2c and P2d ------------------------------------------------------


def test_nothing_of_a_story_reaches_the_cluster_file_manifest_receipts_report_logs_or_alert(tmp_path, caplog):
    caplog.set_level(logging.DEBUG)
    link = f"https://{MARK_HOST}/{MARK_PATH}?q={MARK_QUERY}"
    world = World(tmp_path)
    world.add(
        item(f"{MARK_HEADLINE} nifty rally today", link, 8), item(f"{MARK_HEADLINE} nifty rally today", link + "2", 9)
    )
    report = world.cluster()
    public = [
        report.line(),
        report.alert_text(),
        caplog.text,
        (world.record.manifest_folder / "clusters.csv").read_text(),
    ]
    public += [p.read_text() for p in world.record.receipts.folder.rglob("*") if p.is_file()]
    public += [world.drive.get(f"raw/{cluster_path(world.version(), AS_OF)}").decode()]
    for marker in (MARK_HEADLINE, MARK_HOST, MARK_PATH, MARK_QUERY, "Outlet", "nifty", "rally"):
        assert not [text for text in public if marker in text]
    assert (
        MARK_HEADLINE
        in b"".join(p.read_bytes() for p in (world.drive.folder / "raw/news/articles").rglob("*.json")).decode()
    )


# ---- the command ------------------------------------------------------------------------------------------------


NOW = datetime(2026, 10, 27, 12, 41, 7, tzinfo=UTC)  # the clock of the command tests: after the test window ends


def run_command(monkeypatch, world, *argv, now=NOW):
    printed, sent = [], []
    monkeypatch.setattr(news_cli, "now_utc", lambda: now)
    monkeypatch.setattr("fno.ingestion.news.cluster_record.wiring.build_news_cluster", lambda: world.run_object)
    monkeypatch.setattr(
        "fno.ingestion.composition.build_alert_sender",
        lambda: type("A", (), {"send": lambda s, m: sent.append(m) or ""})(),
    )
    args = build_parser().parse_args(["news", "cluster", *argv])
    return news_cli.cmd_news_cluster(args, out=printed.append), printed, sent


def test_the_command_exits_0_without_an_alert_when_the_file_is_written(tmp_path, monkeypatch):
    world = World(tmp_path)
    world.add(item(HEADLINE, "https://pub.example/a/1"))
    code, printed, sent = run_command(monkeypatch, world, "--as-of", "2026-10-27T12:00:00+00:00")
    assert code == 0 and printed[0].endswith("written") and sent == []


def test_a_conflict_exits_1_and_the_alert_says_to_investigate(tmp_path, monkeypatch):
    world = World(tmp_path)
    world.add(item(HEADLINE, "https://pub.example/a/1"))
    run_command(monkeypatch, world, "--as-of", "2026-10-27T12:00:00+00:00")
    world.add(item(OTHER, "https://pub.example/b/1"), hours_after=1)
    code, printed, sent = run_command(monkeypatch, world, "--as-of", "2026-10-27T12:00:00+00:00")
    assert (
        code == 1
        and "cluster_conflict 1" in printed[0]
        and "investigate" in sent[0]
        and "never" not in sent[0].replace("nothing was overwritten", "")
    )


def test_an_unexpected_error_prints_only_its_class(monkeypatch):
    def boom():
        raise ValueError(f"leaks https://{MARK_HOST}/x")

    printed = []
    monkeypatch.setattr("fno.ingestion.news.cluster_record.wiring.build_news_cluster", boom)
    monkeypatch.setattr(
        "fno.ingestion.composition.build_alert_sender", lambda: type("A", (), {"send": lambda s, m: ""})()
    )
    args = build_parser().parse_args(["news", "cluster"])
    assert news_cli.cmd_news_cluster(args, out=printed.append) == 1
    assert printed[0] == "news cluster stopped: unexpected_error ValueError" and MARK_HOST not in "".join(printed)


def test_a_window_end_without_a_zone_is_refused():
    import pytest

    with pytest.raises(SystemExit):
        build_parser().parse_args(["news", "cluster", "--as-of", "2026-10-27T12:00:00"])


def test_the_default_window_end_is_the_current_hour_floored(tmp_path, monkeypatch):
    world = World(tmp_path)
    seen = []
    monkeypatch.setattr(
        world.run_object,
        "run",
        lambda as_of: (
            seen.append(as_of) or type("R", (), {"line": lambda s: "x", "ok": True, "alert_text": lambda s: "x"})()
        ),
    )
    run_command(monkeypatch, world)
    assert seen == [datetime(2026, 10, 27, 12, 0, 0, tzinfo=UTC)]


# ---- the workflow ------------------------------------------------------------------------------------------------


def test_the_cluster_workflow_is_dispatch_only_serial_with_promote_and_uses_the_one_guard():
    text = (ROOT / ".github/workflows/news-cluster.yml").read_text()
    flow = yaml.safe_load(text)
    (job,) = flow["jobs"].values()
    promote = yaml.safe_load((ROOT / ".github/workflows/news-promote.yml").read_text())
    assert set(flow[True]) == {"workflow_dispatch"} and "cron" not in text
    assert flow["concurrency"] == promote["concurrency"] and flow["concurrency"]["cancel-in-progress"] is False
    assert job["env"]["MANIFEST"] == "research/data/manifests/news/clusters.csv"
    assert job["env"]["RECEIPTS"] == "receipts/raw/news/clusters receipts/_batches"
    commit = next(s for s in job["steps"] if s.get("name", "").startswith("Commit the cluster manifest"))
    assert commit["run"] == "bash ops/commit_news_record.sh" and commit["if"] == "${{ !inputs.dry_run }}"
    cluster = next(s for s in job["steps"] if s.get("id") == "cluster")
    assert cluster["continue-on-error"] is True
    last = job["steps"][-1]
    assert last["if"] == "${{ failure() && !inputs.dry_run }}" and "build_alert_sender" in last["run"]


def test_nothing_in_the_package_prints_or_reads_a_clock_and_the_shared_writer_is_the_only_putter():
    """NP2c moved the one `put` into `news/write_once.py`, which ClusterWriter extends: still one place that writes."""
    package = ROOT / "fno/ingestion/news/cluster_record"
    puts = {}
    for file in [*package.glob("*.py"), ROOT / "fno/ingestion/news/write_once.py"]:
        for node in ast.walk(ast.parse(file.read_text())):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "put":
                    puts.setdefault(file.name, 0)
                    puts[file.name] += 1
                assert node.func.attr not in {"now", "utcnow", "today"}, file.name
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id != "print", file.name
    assert puts == {"write_once.py": 1}


def test_a_window_end_later_than_this_hour_is_refused_with_a_fixed_code_and_nothing_runs(tmp_path, monkeypatch):
    """judge 54 F2: a future window end would write a file that a later run of the same name could never match."""
    world = World(tmp_path)
    world.add(item(HEADLINE, "https://pub.example/a/1"))
    code, printed, sent = run_command(monkeypatch, world, "--as-of", "2026-10-27T13:00:00+00:00")
    assert code == 1 and printed[0] == "news cluster stopped: window_in_future" and len(sent) == 1
    assert world.cluster_files() == []


def test_this_hour_and_earlier_hours_are_accepted(tmp_path, monkeypatch):
    world = World(tmp_path)
    world.add(item(HEADLINE, "https://pub.example/a/1"))
    assert run_command(monkeypatch, world, "--as-of", "2026-10-27T12:00:00+00:00")[0] == 0
    assert run_command(monkeypatch, world, "--as-of", "2026-10-27T11:00:00+00:00")[0] == 0


def test_a_window_end_one_second_after_this_hour_is_refused_and_exactly_this_hour_is_not(tmp_path, monkeypatch):
    world = World(tmp_path)
    world.add(item(HEADLINE, "https://pub.example/a/1"))
    assert run_command(monkeypatch, world, "--as-of", "2026-10-27T12:00:01+00:00")[1][0].endswith("window_in_future")
    assert run_command(monkeypatch, world, "--as-of", "2026-10-27T12:00:00+00:00")[0] == 0
