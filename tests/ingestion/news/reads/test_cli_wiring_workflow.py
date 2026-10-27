"""NP4b: the command, its composition root and the dispatch-only workflow."""

from __future__ import annotations

import datetime
from argparse import Namespace
from pathlib import Path

import yaml

from fno.ingestion.news import codes
from fno.ingestion.news.reads import cli as read_cli
from fno.ingestion.news.reads import wiring
from fno.ingestion.news.reads.run import PAGES, ReadPass
from tests.ingestion.news.reads.helpers import World

ROOT = Path(__file__).resolve().parents[4]


class Command:
    def __init__(self, monkeypatch, world: World):
        self.lines, self.alerts, self.args = [], [], []
        pass_ = world.read_pass()
        real = pass_.run

        def run(today, apply, pages):
            self.args.append((apply, pages))
            return real(today, apply, pages)

        pass_.run = run
        monkeypatch.setattr(wiring, "build_read_pass", lambda env=None: pass_)
        monkeypatch.setattr("fno.shared.models.now_utc", lambda: datetime.datetime(2026, 10, 27, 12, 0))
        sender = type("Sender", (), {"send": lambda _, text: self.alerts.append(text) or "sent"})()
        monkeypatch.setattr("fno.ingestion.composition.build_alert_sender", lambda: sender)

    def run(self, apply=False, limit=PAGES) -> int:
        return read_cli.cmd_news_read_pages(Namespace(apply=apply, limit=limit), out=self.lines.append)


def test_the_command_defaults_to_the_probe_and_the_limit_never_exceeds_the_cap(tmp_path, monkeypatch):
    world = World(tmp_path)
    world.add_publisher(1)
    command = Command(monkeypatch, world)
    assert command.run() == 0 and command.args == [(False, PAGES)] and world.read_files() == []
    assert command.run(apply=True, limit=5000) == 0 and command.args[-1] == (True, PAGES)
    assert command.run(apply=True, limit=-3) == 0 and command.args[-1] == (True, 0)
    assert command.alerts == []


def test_a_failing_reader_exits_1_and_alerts_the_same_counts_only_line(tmp_path, monkeypatch):
    from fno.ingestion.news.pages import model
    from tests.ingestion.news.reads.helpers import Page

    world = World(tmp_path)
    world.add_publisher(1, 2, 3)
    for n in (1, 2, 3):
        world.fetcher.answers[f"https://pub.example/p/{n}"] = Page(model.REFUSED, "")
    command = Command(monkeypatch, world)
    assert command.run(apply=True) == 1
    assert (
        command.alerts == [f"Omenix F&O news read-pages: {command.lines[0]}"]
        and codes.READER_FAILING in command.lines[0]
    )


def test_an_unexpected_error_prints_only_its_class(tmp_path, monkeypatch):
    world = World(tmp_path)
    command = Command(monkeypatch, world)
    monkeypatch.setattr(wiring, "build_read_pass", lambda env=None: (_ for _ in ()).throw(ValueError("https://secret")))
    stopped = f"news read-pages stopped: {codes.UNEXPECTED} ValueError"
    assert command.run() == 1 and command.lines[0] == stopped and "secret" not in repr(command.lines + command.alerts)


def test_the_wiring_builds_a_pass_that_reads_the_record_and_writes_only_read_files(tmp_path, monkeypatch):
    from fno.ingestion.storage.batch_receipts import BatchReceiptWriter
    from fno.ingestion.storage.receipts import ReceiptFolder

    world = World(tmp_path)
    monkeypatch.setattr(wiring, "build_owner_drive", lambda env=None: world.drive)
    monkeypatch.setattr(wiring, "POLL_LOG_FOLDER", world.record.manifest_folder)
    monkeypatch.setattr(wiring, "build_page_fetcher", lambda: world.fetcher)
    monkeypatch.setattr(
        wiring, "batch_receipt_writer", lambda run_id: BatchReceiptWriter(ReceiptFolder(tmp_path / "r"), run_id)
    )
    built = wiring.build_read_pass()
    assert isinstance(built, ReadPass) and built.writer.manifest.log.path.name == "reads.csv"
    assert built.record.area == "raw" and built.wrappers.log.path.name == "wrappers.csv"
    assert built.resolved.log.path.name == "resolved.csv" and built.articles.log.path.name == "articles.csv"
    # judge 109 B2: production wires the planner and the pass notes, or the materiality file would again do nothing
    from fno.ingestion.news.reads.pass_note import PassNotes
    from fno.ingestion.news.reads.plan import ReadPlanner

    assert isinstance(built.planner, ReadPlanner) and isinstance(built.notes, PassNotes)
    assert built.notes.writer.manifest.log.path.name == "read-passes.csv" and built.planner.notes is built.notes


def workflow() -> dict:
    return yaml.safe_load((ROOT / ".github/workflows/news-read-pages.yml").read_text())


def test_the_workflow_is_dispatch_only_serial_with_the_record_and_never_applies_by_default():
    document = workflow()
    triggers = document.get("on", document.get(True))
    assert set(triggers) == {"workflow_dispatch"}
    assert document["concurrency"]["group"] == "news-record" and document["concurrency"]["cancel-in-progress"] is False
    assert triggers["workflow_dispatch"]["inputs"]["apply"]["default"] is False


def test_the_workflow_commits_only_its_own_manifest_and_receipts_and_only_with_apply():
    text = (ROOT / ".github/workflows/news-read-pages.yml").read_text()
    assert "MANIFEST: research/data/manifests/news/reads.csv" in text and "ops/commit_news_record.sh" in text
    assert "RECEIPTS: receipts/raw/news/reads receipts/raw/news/read-passes receipts/_batches" in text
    assert "EXTRA_MANIFESTS: research/data/manifests/news/read-passes.csv" in text  # the pass notes (NP8, judge 105 B1)
    steps = {s.get("name", ""): s for s in workflow()["jobs"]["read"]["steps"]}
    commit = next(s for n, s in steps.items() if n.startswith("Commit the reads manifest"))
    assert "inputs.apply" in commit["if"] and "!inputs.dry_run" in commit["if"]
    assert "--no-verify" not in text and "core.hooksPath .githooks" in text and "schedule:" not in text


def test_loading_the_command_line_does_not_load_the_html_parser():
    """judge 91 M1: the commit guard runs `news check-manifest`; it must not depend on an extractor-only package."""
    import subprocess
    import sys

    code = "import sys, fno.ingestion.cli; sys.exit(1 if 'selectolax' in sys.modules else 0)"
    done = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
