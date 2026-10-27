"""P2a, judge 44 F1 and F3: the privacy line through the REAL news session against a real local HTTP server (the
fake session never reaches urllib3 or the pacer's log). Logging is captured at DEBUG; the committed pause log and the
alerts are the real ones."""

from __future__ import annotations

import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from fno.ingestion.news import codes
from fno.ingestion.news.feeds import FeedEntry, FeedList
from fno.ingestion.news.fetcher import NewsFetcher
from fno.ingestion.news.session import NEWS_PACER, NewsSession
from fno.ingestion.news.snapshot_log import NewsSnapshotLog
from fno.ingestion.promotion.staging import StagingArea
from fno.ingestion.storage.raw_store import LocalFolderStore
from fno.shared.http_pacing import SHARED_PACER, PacedSession
from fno.shared.resilience.transition_log import LayeredLog
from tests.ingestion.news.fakes import MARK_PATH, MARK_QUERY, NOW, RSS


class Server:
    def __init__(self, status):
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                self.send_response(status)
                self.send_header("Content-Length", str(len(RSS) if status == 200 else 0))
                self.end_headers()
                if status == 200:
                    self.wfile.write(RSS)

            def log_message(self, *args):
                pass

        self.httpd = HTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.httpd.server_port}/{MARK_PATH}?q={MARK_QUERY}"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


@pytest.fixture
def quick_pacers(monkeypatch):
    for pacer in (NEWS_PACER, SHARED_PACER):
        monkeypatch.setattr(pacer, "sleep", lambda seconds: None)  # spacing never sleeps for real


def run_news(tmp_path, server, session):
    drive, repo = LocalFolderStore(tmp_path / "drive"), tmp_path / "repo"
    fetcher = NewsFetcher(session, StagingArea(drive), NewsSnapshotLog(repo), lambda: NOW)
    feeds = FeedList(1, tuple(FeedEntry(f"feed-{n:02d}", server.url) for n in (1, 2, 3)))
    return fetcher.run(feeds), repo


def test_urllib3_is_kept_quiet_so_the_query_never_reaches_the_logs_even_at_debug(tmp_path, caplog, quick_pacers):
    server = Server(200)
    try:
        caplog.set_level(logging.DEBUG)
        report, _ = run_news(tmp_path, server, NewsSession())
        assert report.counts == {codes.FETCHED: 3}  # the real session really fetched
        assert MARK_QUERY not in caplog.text and MARK_PATH not in caplog.text
    finally:
        server.close()


def attached_pause_log(tmp_path, alerts):
    log = LayeredLog(tmp_path / "committed.csv", tmp_path / "run.csv")
    SHARED_PACER.attach(log, type("A", (), {"send": lambda self, text: alerts.append(text) or text})())
    return tmp_path / "committed.csv", tmp_path / "run.csv"


def test_a_news_host_that_refuses_us_is_paused_in_process_and_never_written_to_the_pause_log_or_alerts(
    tmp_path, quick_pacers
):
    alerts = []
    committed, run_local = attached_pause_log(tmp_path, alerts)
    server = Server(429)
    try:
        report, _ = run_news(tmp_path, server, NewsSession())
    finally:
        server.close()
    assert report.counts[codes.REFUSED] == 1 and codes.HOST_BLOCKED in report.counts
    assert "127.0.0.1" in NEWS_PACER._hosts  # the news pacer did keep its own state for the run
    assert not committed.exists() and not run_local.exists() and alerts == []


def test_the_control_the_shared_session_does_write_a_refused_host_to_the_pause_log(tmp_path, quick_pacers):
    """Without this the test above could pass because nothing is ever logged."""
    alerts = []
    committed, run_local = attached_pause_log(tmp_path, alerts)
    server = Server(429)
    try:
        session = PacedSession()
        for _ in range(2):  # two refusals in a row pause the host
            session.get(server.url, timeout=10)
    finally:
        server.close()
    assert run_local.exists() and "127.0.0.1" in run_local.read_text("utf-8") and alerts
