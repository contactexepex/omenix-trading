"""P2a, judge 44 F1 and F3: the privacy line through the REAL news session against a real local HTTP server (the
fake session never reaches urllib3 or the pacer's log). Logging is captured at DEBUG; the committed pause log and the
alerts are the real ones."""

from __future__ import annotations

import logging
from http.server import BaseHTTPRequestHandler

import pytest
import requests
from requests.adapters import BaseAdapter

from fno.ingestion.news import codes
from fno.ingestion.news.feeds import FeedEntry, FeedList
from fno.ingestion.news.fetcher import NewsFetcher
from fno.ingestion.news.session import NEWS_PACER, NewsSession
from fno.ingestion.news.snapshot_log import NewsSnapshotLog
from fno.ingestion.promotion.staging import StagingArea
from fno.ingestion.storage.raw_store import AreaStore, LocalFolderStore
from fno.shared.http_pacing import SHARED_PACER, PacedSession
from fno.shared.resilience.transition_log import LayeredLog
from tests.ingestion.news.fakes import MARK_HOST, MARK_PATH, MARK_QUERY, NOW, RSS, LocalServer


class Server(LocalServer):
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

        super().__init__(Handler)
        self.url = f"{self.base}/{MARK_PATH}?q={MARK_QUERY}"


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


# ---- judge 45: the fetcher's store is the staging area; a marker host through the real pacer ------------------


def test_the_wired_fetcher_writes_only_under_staging_and_reads_the_feed_list_from_config(tmp_path, monkeypatch):
    from fno.ingestion.news import wiring
    from tests.ingestion.news.fakes import FEED_URL, Reply, Session, put_version

    class Recording(LocalFolderStore):
        saved: list = []

        def put(self, path, data):
            self.saved.append(path)
            super().put(path, data)

    drive = Recording(tmp_path / "drive")
    drive.saved = []
    put_version(AreaStore(drive, wiring.CONFIG_AREA), 1, FEED_URL)
    drive.saved.clear()
    monkeypatch.setattr(wiring, "build_owner_drive", lambda env: drive)

    class PacedFake(Session):
        def pace_for(self, feeds):  # the real session builds this run's pacer from the feed list (NP3b)
            pass

    monkeypatch.setattr(wiring, "NewsSession", lambda: PacedFake(**{FEED_URL: Reply()}))
    monkeypatch.setattr(wiring, "POLL_LOG_FOLDER", tmp_path / "repo")
    assert wiring.build_news_fetch({}).run().ok
    assert drive.saved and all(path.startswith("staging/news/") for path in drive.saved)  # never `raw/` (the Record)


def test_two_refusals_from_a_marker_host_leave_no_trace_in_the_pause_log_or_the_alerts(tmp_path, quick_pacers):
    alerts = []
    committed, run_local = attached_pause_log(tmp_path, alerts)
    url = f"https://{MARK_HOST}/{MARK_PATH}?q={MARK_QUERY}"

    class Refusing(BaseAdapter):
        def send(self, request, **kwargs):
            response = requests.Response()
            response.status_code, response._content, response.url = 429, b"", request.url
            return response

        def close(self):
            pass

    session = NewsSession()
    session.mount("https://", Refusing())
    feeds = FeedList(1, (FeedEntry("feed-01", url),))
    drive = LocalFolderStore(tmp_path / "drive")
    fetcher = NewsFetcher(session, StagingArea(drive), NewsSnapshotLog(tmp_path / "repo"), lambda: NOW)
    for _ in range(2):  # two refusals in a row open a host's breaker on the shared pacer
        assert fetcher.run(feeds).counts == {codes.REFUSED: 1}
    assert NEWS_PACER._hosts[MARK_HOST].breaker.state.value == "open"
    assert not committed.exists() and not run_local.exists() and alerts == []
    assert MARK_HOST not in "".join(p.read_text("utf-8") for p in (tmp_path / "repo").rglob("*") if p.is_file())
