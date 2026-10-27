"""The master privacy test of P2 (invariant 1), at the fetch layer: a marker URL, query, host and headline run through
the fetcher and the command, including the failure paths, with logging captured at DEBUG. None of the markers may
appear in anything committed or public: the poll log, the report, the alert, the printed output, the logs, the
staging path names or the exceptions. The raw bytes in Staging do hold the headline (they live in private Drive);
that is the one place allowed. Also: the committed tree holds no feed URL."""

from __future__ import annotations

import logging
import re
from pathlib import Path

import requests

from fno.ingestion.news import cli as news_cli
from fno.ingestion.news.feeds import FeedListError, PrivateFeedLists
from fno.ingestion.news.fetcher import NewsFetcher
from fno.ingestion.news.job import NewsFetchJob
from fno.ingestion.news.snapshot_log import NewsSnapshotLog
from fno.ingestion.promotion.staging import StagingArea
from fno.ingestion.storage.raw_store import LocalFolderStore
from tests.ingestion.news.fakes import (
    CONSENT_PAGE,
    FEED_URL,
    MARK_HEADLINE,
    MARK_PATH,
    MARK_QUERY,
    MARKERS,
    NOW,
    OTHER_URL,
    Reply,
    Session,
    put_version,
)

ROOT = Path(__file__).resolve().parents[3]
THIRD_URL = f"https://third-host-zz46.example/{MARK_PATH}?q={MARK_QUERY}"


def leaks(text: str) -> list[str]:
    return [m for m in MARKERS if m in text]


def test_no_marker_reaches_anything_committed_or_public_on_any_path(tmp_path, monkeypatch, caplog, capsys):
    caplog.set_level(logging.DEBUG)
    drive, repo = LocalFolderStore(tmp_path / "drive"), tmp_path / "repo"
    put_version(drive, 1, FEED_URL, OTHER_URL, THIRD_URL)
    wrapped = f"could not reach {FEED_URL} {MARK_HEADLINE}"
    session = Session(
        **{
            FEED_URL: requests.ConnectionError(wrapped),  # a request error whose message holds the URL
            OTHER_URL: Reply(200, CONSENT_PAGE),  # a block page that quotes the headline and the URL
            THIRD_URL: Reply(),  # a good poll
        }
    )
    log = NewsSnapshotLog(repo)
    run = NewsFetchJob(PrivateFeedLists(drive), NewsFetcher(session, StagingArea(drive), log, lambda: NOW), log)
    alerts = []
    monkeypatch.setattr("fno.ingestion.news.wiring.build_news_fetch", lambda: run)
    monkeypatch.setattr(
        "fno.ingestion.composition.build_alert_sender",
        lambda: type("A", (), {"send": lambda self, text: alerts.append(text) or text})(),
    )
    code = news_cli.cmd_news_fetch(None)
    out = capsys.readouterr()
    committed = "".join(p.read_text("utf-8") for p in repo.rglob("*") if p.is_file())
    staged_names = " ".join(str(p.relative_to(tmp_path / "drive")) for p in (tmp_path / "drive").rglob("*"))
    assert code == 1 and committed  # the good poll made a row; the run was not clean
    assert not leaks(committed + out.out + out.err + " ".join(alerts) + caplog.text)
    assert not leaks(staged_names.replace("feeds/", ""))  # the staging path names carry feed ids, not the URL
    # the raw bytes of the good poll are in private Drive, headline included: that is where they belong
    assert any(
        MARK_HEADLINE.encode() in p.read_bytes() for p in (tmp_path / "drive" / "news").rglob("*") if p.is_file()
    )


def test_a_feed_list_error_message_holds_only_its_code():
    try:
        raise FeedListError("feed_list_invalid")
    except FeedListError as error:
        assert not leaks(str(error) + repr(error))


def test_no_feed_url_is_in_the_committed_tree():
    pattern = re.compile(r"news\.google\.com|rss/search|/rss\?q=|[?&]q=[A-Za-z]", re.IGNORECASE)
    scanned = [ROOT / "config.yaml", *sorted((ROOT / "fno").rglob("*.py")), *sorted((ROOT / ".github").rglob("*.yml"))]
    assert len(scanned) > 100  # the walk found the code
    found = [f"{p.relative_to(ROOT)}" for p in scanned if pattern.search(p.read_text("utf-8"))]
    assert found == []
