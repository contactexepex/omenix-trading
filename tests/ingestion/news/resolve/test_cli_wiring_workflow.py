"""NP2c: the command, its composition root and the dispatch-only workflow."""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import yaml

from fno.ingestion.news import codes
from fno.ingestion.news.feeds import FeedEntry
from fno.ingestion.news.resolve import cli as resolve_cli
from fno.ingestion.news.resolve import wiring
from fno.ingestion.news.resolve.model import DECODE_FAILED, Resolved
from fno.ingestion.news.resolve.resolution_file import key_of_path, resolution_path
from fno.ingestion.news.resolve.run import CAP
from fno.ingestion.storage.batch_receipts import BatchReceiptWriter
from fno.ingestion.storage.raw_store import AreaStore
from fno.ingestion.storage.receipts import ReceiptFolder
from tests.ingestion.news.resolve.pass_helpers import FakeResolver, World, wrapper_item

ROOT = Path(__file__).resolve().parents[4]


class Command:
    """`cmd_news_resolve` with the pass, the clock and the alert sender replaced."""

    def __init__(self, monkeypatch, world: World):
        self.lines: list[str] = []
        self.alerts: list[str] = []
        self.args: list[tuple] = []
        pass_ = world.pass_()
        real_run = pass_.run

        def run(today, apply, cap):
            self.args.append((apply, cap))
            return real_run(today, apply, cap)

        pass_.run = run
        monkeypatch.setattr(wiring, "build_resolve_pass", lambda env=None: pass_)
        monkeypatch.setattr(resolve_cli, "now_utc", lambda: __import__("datetime").datetime(2026, 10, 27, 12, 0))
        sender = type("Sender", (), {"send": lambda _, text: self.alerts.append(text) or "sent"})()
        monkeypatch.setattr("fno.ingestion.composition.build_alert_sender", lambda: sender)

    def run(self, apply=False, limit=CAP) -> int:
        return resolve_cli.cmd_news_resolve(Namespace(apply=apply, limit=limit), out=self.lines.append)


def test_the_command_defaults_to_the_probe_and_the_limit_never_exceeds_the_cap(tmp_path, monkeypatch):
    world = World(tmp_path)
    world.add(wrapper_item(1))
    command = Command(monkeypatch, world)
    assert command.run() == 0 and command.args == [(False, CAP)] and world.resolution_files() == []
    assert command.run(apply=True, limit=5000) == 0 and command.args[-1] == (True, CAP)
    assert command.run(apply=True, limit=-3) == 0 and command.args[-1] == (True, 0)
    assert command.alerts == []


def test_a_pass_that_needs_fixing_by_hand_exits_1_and_alerts_the_same_counts_only_line(tmp_path, monkeypatch):
    world = World(tmp_path)
    world.add(wrapper_item(1))
    for article in (world.drive.folder / "raw/news/articles").rglob("*.json"):
        article.write_bytes(b"x")
    command = Command(monkeypatch, world)
    assert command.run(apply=True) == 1
    assert (
        command.alerts == [f"Omenix F&O news resolve: {command.lines[0]}"]
        and codes.ARTICLE_UNREADABLE in command.lines[0]
    )


def test_links_about_to_expire_alert_but_do_not_turn_the_run_red(tmp_path, monkeypatch):
    world = World(tmp_path, FakeResolver({}))
    world.add(wrapper_item(1), wrapper_item(2), days_ago=3)
    world.resolver.answers["https://wrap.svc.example/rss/articles/CBMi0001?oc=5"] = Resolved(DECODE_FAILED)
    command = Command(monkeypatch, world)
    assert command.run(apply=True) == 0 and len(command.alerts) == 1 and "expiring 1" in command.lines[0]


def test_a_resolver_that_resolves_nothing_exits_1_and_alerts(tmp_path, monkeypatch):
    world = World(tmp_path, FakeResolver({}))
    world.resolver.default = Resolved(DECODE_FAILED)
    world.add(wrapper_item(1), wrapper_item(2))
    command = Command(monkeypatch, world)
    assert command.run(apply=True) == 1 and len(command.alerts) == 1 and codes.RESOLVER_FAILING in command.lines[0]


def test_an_unexpected_error_prints_only_its_class(tmp_path, monkeypatch):
    world = World(tmp_path)
    command = Command(monkeypatch, world)
    monkeypatch.setattr(
        wiring, "build_resolve_pass", lambda env=None: (_ for _ in ()).throw(ValueError("https://secret"))
    )
    stopped = f"news resolve stopped: {codes.UNEXPECTED} ValueError"
    assert (
        command.run() == 1 and command.lines[0] == stopped and command.alerts == [f"Omenix F&O news resolve: {stopped}"]
    )
    assert "secret" not in repr(command.lines) + repr(command.alerts)


# ---- the composition root ----------------------------------------------------------------------------------------


def test_the_wiring_builds_one_resolver_for_the_whole_run_from_the_private_feed_list(tmp_path, monkeypatch):
    world = World(tmp_path)
    AreaStore(world.drive, "config").put(
        "feeds/feeds-v1.json",
        b'{"salt":"'
        + b"s" * 32
        + b'","feeds":[{"id":"feed-01","url":"https://search.svc.example/s","kind":"wrapper"}]}',
    )
    built = []
    monkeypatch.setattr(wiring, "build_owner_drive", lambda env=None: world.drive)
    monkeypatch.setattr(wiring, "POLL_LOG_FOLDER", world.record.manifest_folder)
    monkeypatch.setattr(
        wiring,
        "batch_receipt_writer",
        lambda run_id: BatchReceiptWriter(ReceiptFolder(tmp_path / "r" / "receipts"), run_id),
    )

    def build(feeds):
        built.append([f.host for f in feeds if isinstance(f, FeedEntry)])
        return FakeResolver()

    monkeypatch.setattr(wiring, "build_link_resolver", build)
    pass_ = wiring.build_resolve_pass()
    world.add(wrapper_item(1))
    pass_.run(__import__("datetime").date(2026, 10, 27), True)
    pass_.run(__import__("datetime").date(2026, 10, 27), True)
    assert built == [["search.svc.example"]]  # one resolver, built once, from the wrapper feed hosts


def test_the_manifest_id_of_a_resolution_file_is_its_article_key():
    key = "ab" + "c" * 62
    assert key_of_path(resolution_path(key)) == key and resolution_path(key) == f"news/resolved/ab/{key}.json"


# ---- the workflow ----------------------------------------------------------------------------------------------


def workflow() -> dict:
    return yaml.safe_load((ROOT / ".github/workflows/news-resolve.yml").read_text())


def test_the_workflow_is_dispatch_only_serial_with_the_record_and_never_applies_by_default():
    document = workflow()
    triggers = document.get("on", document.get(True))
    assert set(triggers) == {"workflow_dispatch"}  # no schedule until the owner enables one at go-live
    assert document["concurrency"]["group"] == "news-record" and document["concurrency"]["cancel-in-progress"] is False
    inputs = triggers["workflow_dispatch"]["inputs"]
    assert inputs["apply"]["default"] is False and inputs["dry_run"]["default"] is False


def test_the_workflow_commits_only_its_own_manifest_and_receipts_through_the_shared_guard():
    text = (ROOT / ".github/workflows/news-resolve.yml").read_text()
    assert "MANIFEST: research/data/manifests/news/resolved.csv" in text and "ops/commit_news_record.sh" in text
    assert "RECEIPTS: receipts/raw/news/resolved receipts/_batches" in text
    steps = {s.get("name", ""): s for s in workflow()["jobs"]["resolve"]["steps"]}
    commit = next(s for n, s in steps.items() if n.startswith("Commit the resolved-files manifest"))
    assert "inputs.apply" in commit["if"] and "!inputs.dry_run" in commit["if"]  # a probe commits nothing (judge 83)
    assert "--no-verify" not in text and "core.hooksPath .githooks" in text
    assert "schedule:" not in text and "cron" not in text
