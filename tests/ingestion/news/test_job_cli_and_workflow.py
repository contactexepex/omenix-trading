"""One news run (P2a): the feed list is checked before any request, the command's exit code and alert, the parser, and
the workflow that must stay manual (no schedule) until the owner enables one."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from fno.ingestion.cli import build_parser
from fno.ingestion.news import cli as news_cli
from fno.ingestion.news import codes
from fno.ingestion.news.feeds import FeedListError, PrivateFeedLists
from fno.ingestion.news.fetcher import NewsFetcher
from fno.ingestion.news.job import NewsFetchJob
from fno.ingestion.news.snapshot_log import NewsSnapshotLog, PollRow
from fno.ingestion.promotion.staging import StagingArea
from fno.ingestion.storage.raw_store import LocalFolderStore
from tests.ingestion.news.fakes import FEED_URL, NOW, Reply, Session, put_version

ROOT = Path(__file__).resolve().parents[3]


def job(tmp_path, session):
    drive = LocalFolderStore(tmp_path / "drive")
    log = NewsSnapshotLog(tmp_path / "repo")
    fetcher = NewsFetcher(session, StagingArea(drive), log, lambda: NOW)
    return NewsFetchJob(PrivateFeedLists(drive), fetcher, log), drive, log


def test_a_missing_list_stops_the_run_before_any_request(tmp_path):
    session = Session()
    run, _, _ = job(tmp_path, session)
    with pytest.raises(FeedListError, match=codes.FEED_LIST_MISSING):
        run.run()
    assert session.asked == []


def test_a_list_older_than_the_newest_one_already_used_stops_the_run(tmp_path):
    session = Session(**{FEED_URL: Reply()})
    run, drive, log = job(tmp_path, session)
    put_version(drive, 1, FEED_URL)
    log.append(PollRow(NOW, "feed-01", "p", "0" * 64, 1, 2))  # a poll already made with version 2
    with pytest.raises(FeedListError, match=codes.FEED_LIST_ROLLED_BACK):
        run.run()
    assert session.asked == []


def test_the_command_exits_0_and_sends_no_alert_when_every_feed_is_fetched(tmp_path, monkeypatch):
    run, drive, _ = job(tmp_path, Session(**{FEED_URL: Reply()}))
    put_version(drive, 1, FEED_URL)
    alerts, printed = [], []
    monkeypatch.setattr("fno.ingestion.news.wiring.build_news_fetch", lambda: run)
    monkeypatch.setattr(
        "fno.ingestion.composition.build_alert_sender", lambda: type("A", (), {"send": alerts.append})()
    )
    assert news_cli.cmd_news_fetch(None, out=printed.append) == 0
    assert printed == ["news fetch: fetched 1"] and alerts == []


@pytest.mark.parametrize("fix", ["block", "no_list"])
def test_anything_else_exits_1_and_alerts_the_same_fixed_line(tmp_path, monkeypatch, fix):
    reply = Reply(429)
    run, drive, _ = job(tmp_path, Session(**{FEED_URL: reply}))
    if fix == "block":
        put_version(drive, 1, FEED_URL)
    alerts, printed = [], []
    monkeypatch.setattr("fno.ingestion.news.wiring.build_news_fetch", lambda: run)
    monkeypatch.setattr(
        "fno.ingestion.composition.build_alert_sender",
        lambda: type("A", (), {"send": lambda self, text: alerts.append(text) or "alert sent"})(),
    )
    assert news_cli.cmd_news_fetch(None, out=printed.append) == 1
    expected = "news fetch: refused 1" if fix == "block" else "news fetch stopped: feed_list_missing"
    assert printed[0] == expected and alerts == [f"Omenix F&O news fetch: {expected}"]


def test_the_command_is_registered():
    assert build_parser().parse_args(["news", "fetch"]).func is news_cli.cmd_news_fetch


def test_news_fetch_workflow_is_manual_only_with_no_schedule():
    document = yaml.safe_load((ROOT / ".github" / "workflows" / "news-fetch.yml").read_text("utf-8"))
    triggers = document[True] if True in document else document["on"]  # YAML reads a bare `on` as the boolean True
    assert set(triggers) == {"workflow_dispatch"}
