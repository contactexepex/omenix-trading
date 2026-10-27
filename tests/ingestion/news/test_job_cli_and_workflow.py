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
from fno.ingestion.news.snapshot_log import NewsSnapshotLog
from fno.ingestion.promotion.staging import StagingArea
from fno.ingestion.storage.raw_store import LocalFolderStore
from tests.ingestion.news.fakes import FEED_URL, NOW, OTHER_URL, Reply, Session, put_version

ROOT = Path(__file__).resolve().parents[3]


def job(tmp_path, session):
    drive = LocalFolderStore(tmp_path / "drive")
    log = NewsSnapshotLog(tmp_path / "repo")
    fetcher = NewsFetcher(session, StagingArea(drive), log, lambda: NOW)
    return NewsFetchJob(PrivateFeedLists(drive), fetcher, log, lambda: NOW), drive, log


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
    log.note_feed_list(2, "f" * 64, NOW)  # version 2 was already used
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


# ---- an edited feed list (the owner's "add a version" rule; Judge 1's verified-cache point) --------------------------


def edit_in_place(drive, version, *urls):
    from tests.ingestion.news.fakes import feed_list_bytes

    (drive.folder / "feeds" / f"feeds-v{version}.json").write_bytes(feed_list_bytes(*urls))


def test_a_new_version_is_read_by_the_next_run_with_no_halt(tmp_path):
    session = Session(**{FEED_URL: Reply(), OTHER_URL: Reply()})
    run, drive, log = job(tmp_path, session)
    put_version(drive, 1, FEED_URL)
    assert run.run().ok and log.highest_feed_list_version() == 1
    put_version(drive, 2, FEED_URL, OTHER_URL)  # the owner adds a feed by adding a version
    second = run.run()
    assert second.ok and log.highest_feed_list_version() == 2 and session.asked.count(OTHER_URL) == 1


def test_a_version_edited_in_place_after_use_is_skipped_the_last_good_one_is_used_and_the_run_is_not_clean(tmp_path):
    session = Session(**{FEED_URL: Reply(), OTHER_URL: Reply()})
    run, drive, _ = job(tmp_path, session)
    put_version(drive, 1, FEED_URL)
    run.run()
    put_version(drive, 2, FEED_URL, OTHER_URL)
    run.run()
    edit_in_place(drive, 2, OTHER_URL)  # version 2 is changed after it was used
    session.asked.clear()
    report = run.run()
    assert report.counts[codes.FEED_LIST_DAMAGED] == 1 and not report.ok  # never silent: the command alerts on this
    assert session.asked == [FEED_URL]  # version 1 was used, not the edited version 2


def test_when_every_version_has_been_edited_the_run_stops_with_a_code_before_any_request(tmp_path):
    session = Session(**{FEED_URL: Reply()})
    run, drive, _ = job(tmp_path, session)
    put_version(drive, 1, FEED_URL)
    run.run()
    edit_in_place(drive, 1, OTHER_URL)
    session.asked.clear()
    with pytest.raises(FeedListError, match=codes.FEED_LIST_DAMAGED):
        run.run()
    assert session.asked == []


def test_the_command_alerts_when_a_version_was_edited_after_use(tmp_path, monkeypatch):
    run, drive, _ = job(tmp_path, Session(**{FEED_URL: Reply(), OTHER_URL: Reply()}))
    put_version(drive, 1, FEED_URL)
    run.run()
    put_version(drive, 2, FEED_URL, OTHER_URL)
    run.run()
    edit_in_place(drive, 2, OTHER_URL)
    alerts = []
    monkeypatch.setattr("fno.ingestion.news.wiring.build_news_fetch", lambda: run)
    monkeypatch.setattr(
        "fno.ingestion.composition.build_alert_sender",
        lambda: type("A", (), {"send": lambda self, text: alerts.append(text) or text})(),
    )
    assert news_cli.cmd_news_fetch(None, out=lambda line: None) == 1
    assert alerts and codes.FEED_LIST_DAMAGED in alerts[0]


def test_a_run_of_only_unchanged_polls_still_records_the_feed_list_version_it_used(tmp_path):
    run, drive, log = job(tmp_path, Session(**{FEED_URL: Reply()}))
    put_version(drive, 1, FEED_URL)
    run.run()
    (tmp_path / "repo" / "polls.csv").unlink()  # forget the poll rows: only the version record is left
    again = run.run()
    assert again.counts == {codes.UNCHANGED: 1} and log.log.rows() == []
    (row,) = log.lists.rows()  # one row per version ever used, however many runs
    assert row["feed_list_version"] == "1" and len(row["feed_list_sha256"]) == 64


def test_the_commit_step_adds_only_the_poll_log_folder():
    document = yaml.safe_load((ROOT / ".github" / "workflows" / "news-fetch.yml").read_text("utf-8"))
    steps = document["jobs"]["fetch"]["steps"]
    adds = [line.strip() for s in steps for line in str(s.get("run", "")).splitlines() if "git add" in line]
    assert adds == ['git add "$POLLS"'] + [
        line for line in adds if "commit_pause_log" in line
    ]  # the pause step is a script
    assert document["jobs"]["fetch"]["env"]["POLLS"] == "research/data/manifests/news"
