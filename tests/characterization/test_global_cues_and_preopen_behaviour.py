"""Story R1d4, step 0: today's exact behaviour of the Yahoo source and the pre-open reader, pinned BEFORE any of it
moves onto the shared resilience layer. Yahoo's block rule (a block is a stop, never retried another way, one
block stops the whole run), the pre-open statuses, and the order raw-bytes-first. No network, no real clock. Passes
on `main` unchanged."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest
import requests

from fno.ingestion.global_cues.markets import NEW_YORK, SEOUL, TOKYO
from fno.ingestion.global_cues.preopen import (
    CLOSED,
    FAILED,
    LIVE,
    LUNCH,
    NO_DATA,
    ROW_FIELDS,
    STALE,
    PreopenReader,
)
from fno.ingestion.global_cues.snapshot_log import SnapshotLog
from fno.ingestion.global_cues.source import TIMEOUT_SECONDS, CueRequest
from fno.ingestion.global_cues.yahoo_source import BLOCK_STATUSES, YahooBlocked, YahooChartSource, YahooGate
from fno.ingestion.storage.row_log import RowLog

CHART = b'{"chart":{"result":[{"meta":{"exchangeTimezoneName":"Asia/Tokyo"},"indicators":{"quote":[{"close":[1.0]}]},'
CHART += b'"timestamp":[1]}]}}'


class Reply:
    def __init__(self, status=200, content=CHART, redirect=False):
        self.status_code, self.content, self.is_redirect = status, content, redirect

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}", response=self)


class Scripted:
    def __init__(self, *script):
        self.script, self.calls = list(script), []

    def get(self, url, **kw):
        self.calls.append((url, kw))
        step = self.script.pop(0)
        if isinstance(step, BaseException):
            raise step
        return step


def source(gate=None, market=TOKYO, cue="nikkei"):
    return YahooChartSource(cue, "^N225", market, 7, False, gate)


REQUEST = CueRequest("x.json", "https://example.test/chart")


@pytest.mark.parametrize("status", BLOCK_STATUSES)
def test_a_block_status_raises_blocked_and_is_never_retried(status):
    session = Scripted(Reply(status))
    with pytest.raises(YahooBlocked):
        source().download(session, REQUEST)
    assert len(session.calls) == 1


def test_block_statuses_are_401_403_429():
    assert BLOCK_STATUSES == (401, 403, 429)


def test_a_redirect_is_a_block_and_redirects_are_not_followed():
    session = Scripted(Reply(302, redirect=True))
    with pytest.raises(YahooBlocked):
        source().download(session, REQUEST)
    assert session.calls[0][1] == {"timeout": TIMEOUT_SECONDS, "allow_redirects": False}


@pytest.mark.parametrize("content", [b"<html>consent</html>", b'{"finance":{"error":1}}'])
def test_a_page_or_error_answer_is_a_block(content):
    with pytest.raises(YahooBlocked):
        source().download(Scripted(Reply(200, content)), REQUEST)


def test_a_server_error_is_raised_as_is_not_a_block_and_not_retried():
    session = Scripted(Reply(503))
    gate = YahooGate()
    with pytest.raises(requests.HTTPError):
        source(gate).download(session, REQUEST)
    assert len(session.calls) == 1 and gate.blocked == ""


def test_a_dropped_connection_is_raised_not_retried():
    session = Scripted(requests.ConnectionError("down"))
    with pytest.raises(requests.ConnectionError):
        source().download(session, REQUEST)
    assert len(session.calls) == 1


def test_one_block_stops_every_yahoo_cue_of_the_run_with_no_request():
    gate, session = YahooGate(), Scripted(Reply(429))
    with pytest.raises(YahooBlocked):
        source(gate, cue="nikkei").download(session, REQUEST)
    other = Scripted()
    with pytest.raises(YahooBlocked, match="not asked: nikkei was blocked earlier"):
        source(gate, cue="spx", market=NEW_YORK).download(other, REQUEST)
    assert other.calls == []


def test_a_good_answer_is_returned():
    assert source().download(Scripted(Reply()), REQUEST) == CHART


# ---- the pre-open reader ---------------------------------------------------------------------------------------


class MemoryArchive:
    def __init__(self, fail=False):
        self.files, self.fail = {}, fail

    def put(self, path, data):
        if self.fail:
            raise requests.ConnectionError("drive down")
        self.files[path] = data


class MemoryRows(RowLog):
    def __init__(self):
        self.stored = []

    def rows(self):
        return [dict(zip(ROW_FIELDS, r, strict=True)) for r in self.stored]

    def check_appendable(self):
        pass

    def append(self, fields, rows):
        self.stored += rows


def chart(zone, stamps, closes):
    result = {"meta": {"exchangeTimezoneName": zone}, "indicators": {"quote": [{"close": closes}]}}
    if stamps is not None:
        result["timestamp"] = stamps
    return json.dumps({"chart": {"result": [result]}}).encode()


def reader(tmp_path, now, session, archive=None, **kw):
    rows, archive = MemoryRows(), archive or MemoryArchive()
    r = PreopenReader(session, archive, SnapshotLog(tmp_path), rows, lambda i, s: ("", ""), lambda: now, **kw)
    return r, rows, archive


def stamp(moment):
    return int(moment.timestamp())


NOW = datetime(2026, 10, 27, 3, 20, tzinfo=UTC)  # 08:50 IST, 12:20 Tokyo


def test_a_fresh_level_is_live_and_its_raw_bytes_are_kept_with_a_log_row(tmp_path):
    data = chart("Asia/Seoul", [stamp(NOW - timedelta(minutes=7))], [100.0])
    r, rows, archive = reader(tmp_path, NOW, Scripted(Reply(200, data)))
    out = r.read(source(market=SEOUL), "nikkei")
    assert out.status == LIVE and list(archive.files.values()) == [data]
    assert rows.rows()[0]["status"] == LIVE and rows.rows()[0]["sha256"]
    assert SnapshotLog(tmp_path).path_for("nikkei_preopen").is_file()


def test_an_old_level_is_stale(tmp_path):
    data = chart("Asia/Seoul", [stamp(NOW - timedelta(minutes=40))], [100.0])
    r, rows, _ = reader(tmp_path, NOW, Scripted(Reply(200, data)))
    assert r.read(source(market=SEOUL), "nikkei").status == STALE


def test_a_level_from_an_earlier_day_is_market_closed_without_a_calendar(tmp_path):
    data = chart("Asia/Tokyo", [stamp(NOW - timedelta(days=1))], [100.0])
    r, _, _ = reader(tmp_path, NOW, Scripted(Reply(200, data)))
    assert r.read(source(), "nikkei").status == CLOSED


def test_an_empty_chart_is_no_session_data_with_an_incomplete_problem(tmp_path):
    data = chart("Asia/Tokyo", None, [])
    r, rows, archive = reader(tmp_path, NOW, Scripted(Reply(200, data)))
    out = r.read(source(), "nikkei")
    assert out.status == NO_DATA and out.problems[0].kind == "incomplete" and archive.files


def test_a_changed_layout_keeps_the_bytes_and_is_a_failure(tmp_path):
    data = chart("Asia/Tokyo", [1, 2], [100.0])
    r, rows, archive = reader(tmp_path, NOW, Scripted(Reply(200, data)))
    out = r.read(source(), "nikkei")
    assert out.status == FAILED and out.problems[0].kind == "failure" and list(archive.files.values()) == [data]


def test_a_block_stops_the_index_with_one_request_and_nothing_archived(tmp_path):
    session = Scripted(Reply(429))
    r, rows, archive = reader(tmp_path, NOW, session)
    with pytest.raises(YahooBlocked):
        r.read(source(), "nikkei")
    assert len(session.calls) == 1 and archive.files == {} and rows.stored == []


def test_a_drive_failure_while_archiving_writes_no_row(tmp_path):
    data = chart("Asia/Tokyo", [stamp(NOW - timedelta(minutes=7))], [100.0])
    r, rows, _ = reader(tmp_path, NOW, Scripted(Reply(200, data)), archive=MemoryArchive(fail=True))
    with pytest.raises(requests.ConnectionError):
        r.read(source(), "nikkei")
    assert rows.stored == [] and not SnapshotLog(tmp_path).path_for("nikkei_preopen").exists()


def test_the_lunch_break_status_is_reported_inside_a_markets_midday_break(tmp_path):
    at_lunch = datetime(2026, 10, 27, 2, 45, tzinfo=UTC)  # 11:45 Tokyo
    data = chart("Asia/Tokyo", [stamp(at_lunch - timedelta(minutes=30))], [100.0])
    r, _, _ = reader(tmp_path, at_lunch, Scripted(Reply(200, data)))
    assert r.read(source(), "nikkei").status == LUNCH
