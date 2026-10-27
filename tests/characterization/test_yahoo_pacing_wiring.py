"""Story R1d4, the integration the unit floor skipped: in production every Yahoo and pre-open request goes through a
`PacedSession` on the process-wide `SHARED_PACER`, so a Yahoo 429 counts toward the Yahoo HOST's pause there. Two
refusals in a row pause the host and the next index is not asked at all. Also the pre-open stale window to the minute.
Offline, no real sleep. Passes on `main` unchanged."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
import requests
from requests.adapters import BaseAdapter

from fno.ingestion.global_cues import wiring as cue_wiring
from fno.ingestion.global_cues.markets import SEOUL, TOKYO
from fno.ingestion.global_cues.preopen import LIVE, STALE, level_status
from fno.ingestion.global_cues.source import CueRequest
from fno.ingestion.global_cues.yahoo_source import YahooBlocked, YahooChartSource
from fno.ingestion.preopen.wiring import _parts
from fno.shared.http_pacing import SHARED_PACER
from fno.shared.nse_pacer import SourceCoolingOff
from fno.shared.resilience.breaker import State

YAHOO_HOST = "query1.finance.yahoo.com"
REQUEST = CueRequest("x.json", f"https://{YAHOO_HOST}/v8/finance/chart/%5EN225?range=1d&interval=5m")


class Refusing(BaseAdapter):
    """Answers every request with HTTP 429 and counts how many reached the wire."""

    def __init__(self, status=429):
        super().__init__()
        self.status, self.sent = status, 0

    def send(self, request, **kwargs):
        self.sent += 1
        response = requests.Response()
        response.status_code, response.url, response._content = self.status, request.url, b""
        return response

    def close(self):
        pass


@pytest.fixture
def quick_shared_pacer(monkeypatch):
    monkeypatch.setattr(SHARED_PACER, "sleep", lambda seconds: None)  # spacing never sleeps for real
    return SHARED_PACER


def source(cue):
    return YahooChartSource(cue, "^N225", TOKYO, 7, False)  # each with its own gate, as the pre-open sources are


def test_every_session_the_cue_jobs_and_the_preopen_capture_build_is_on_the_shared_pacer():
    assert cue_wiring._session().pacer is SHARED_PACER
    assert all(part.session.pacer is SHARED_PACER for part in _parts({})[:2])


def test_two_yahoo_429s_in_a_row_pause_the_yahoo_host_and_the_third_index_is_not_asked(quick_shared_pacer):
    session, wire = cue_wiring._session(), Refusing(429)
    session.mount("https://", wire)
    for cue in ("nikkei", "kospi"):
        with pytest.raises(YahooBlocked):
            source(cue).download(session, REQUEST)
    assert wire.sent == 2
    assert SHARED_PACER._hosts[YAHOO_HOST].breaker.state is State.OPEN
    with pytest.raises(SourceCoolingOff):
        source("taiex").download(session, REQUEST)
    assert wire.sent == 2  # nothing reached Yahoo: the host is paused


def test_one_yahoo_429_followed_by_a_good_answer_does_not_pause_the_host(quick_shared_pacer):
    session, wire = cue_wiring._session(), Refusing(429)
    session.mount("https://", wire)
    with pytest.raises(YahooBlocked):
        source("nikkei").download(session, REQUEST)
    wire.status = 200
    wire.sent = 0
    good = b'{"chart":{"result":[{}]}}'
    original = wire.send

    def with_body(request, **kwargs):
        response = original(request, **kwargs)
        response._content = good
        return response

    wire.send = with_body
    assert source("kospi").download(session, REQUEST) == good
    assert SHARED_PACER._hosts[YAHOO_HOST].breaker.state is State.CLOSED


# ---- the pre-open stale window, to the minute (orchestrator's item 1) -----------------------------------------------

SEEN = datetime(2026, 10, 27, 3, 20, tzinfo=UTC)  # 08:50 IST, 11:50 in Seoul (no lunch break)


@pytest.mark.parametrize(
    ("age", "status"),
    [
        (timedelta(minutes=19), LIVE),
        (timedelta(minutes=19, seconds=59), LIVE),
        (timedelta(minutes=20), LIVE),
        (timedelta(minutes=20, seconds=1), STALE),
        (timedelta(minutes=21), STALE),
    ],
    ids=["19m", "19m59s", "20m", "20m01s", "21m"],
)
def test_a_level_is_live_up_to_exactly_20_minutes_old_and_stale_from_one_second_over(age, status):
    assert level_status(SEEN, SEEN - age, SEOUL) == status
