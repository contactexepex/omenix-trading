"""Story R1b, step 0: today's exact pacing and public-NSE JSON behaviour, pinned before the refactor.

Pins `RequestPacer` (spacing per host, the pause after two refusals in a row, the 15-minute cool-off, which statuses
count), `PacedSession` and `PublicData.nse_json` (3 tries, waits 1.5 s and 3.0 s, the 0.4 s pause after a success).
Passes on `main` unchanged; the refactor keeps it green. No network, no real sleep."""

from __future__ import annotations

import pytest

from fno.ingestion.providers import public
from fno.shared.http_pacing import COOL_OFF_SECONDS, PacedSession, RequestPacer, SourceCoolingOff

HOST, OTHER = "nsearchives.nseindia.com", "www.nseindia.com"


class Time:
    def __init__(self):
        self.now, self.slept = 1000.0, []

    def clock(self):
        return self.now

    def sleep(self, seconds):
        self.slept.append(seconds)
        self.now += seconds


def pacer():
    t = Time()
    p = RequestPacer(clock=t.clock)
    p.sleep = t.sleep
    return p, t


def test_cool_off_is_fifteen_minutes_and_two_refusals_make_a_pause():
    assert COOL_OFF_SECONDS == 900
    p, t = pacer()
    p.wait_turn(HOST)
    p.observe(HOST, 403)
    p.wait_turn(HOST)  # one refusal alone does not pause
    p.observe(HOST, 403)
    with pytest.raises(SourceCoolingOff, match="15 minutes"):
        p.wait_turn(HOST)
    t.now += 899
    with pytest.raises(SourceCoolingOff):
        p.wait_turn(HOST)
    t.now += 2
    p.wait_turn(HOST)  # the pause has ended


def test_403_and_429_count_together_and_other_statuses_reset():
    p, _ = pacer()
    p.observe(HOST, 429)
    p.observe(HOST, 403)
    with pytest.raises(SourceCoolingOff):
        p.wait_turn(HOST)
    p2, _ = pacer()
    p2.observe(HOST, 403)
    p2.observe(HOST, 200)
    p2.observe(HOST, 403)
    p2.wait_turn(HOST)  # 403, 200, 403 is not two in a row
    for status in (404, 500, 503):  # only 403 and 429 count as refusals
        p3, _ = pacer()
        p3.observe(HOST, status)
        p3.observe(HOST, status)
        p3.wait_turn(HOST)


def test_the_pause_is_per_host():
    p, _ = pacer()
    p.observe(HOST, 403)
    p.observe(HOST, 403)
    p.wait_turn(OTHER)


def test_one_second_spacing_per_host_and_none_between_hosts():
    p, t = pacer()
    p.wait_turn(HOST)
    p.wait_turn(HOST)
    p.wait_turn(HOST)
    assert t.slept == [1.0, 1.0]
    p.wait_turn(OTHER)
    assert t.slept == [1.0, 1.0]


def test_an_unknown_host_gets_the_default_one_second_spacing():
    p, t = pacer()
    p.wait_turn("example.org")
    p.wait_turn("example.org")
    assert t.slept == [1.0]


def test_the_refusal_count_restarts_after_a_pause_begins():
    p, t = pacer()
    p.observe(HOST, 403)
    p.observe(HOST, 403)
    t.now += 901
    p.observe(HOST, 403)
    p.wait_turn(HOST)  # one refusal after the pause is not a new pause


def test_paced_session_waits_its_turn_and_reports_the_status(monkeypatch):
    seen = []

    class Recording(RequestPacer):
        def wait_turn(self, host):
            seen.append(("wait", host))

        def observe(self, host, status):
            seen.append(("observe", host, status))

    class Reply:
        status_code = 403

    monkeypatch.setattr("requests.Session.request", lambda self, method, url, *a, **k: Reply())
    PacedSession(Recording()).get("https://nsearchives.nseindia.com/x")
    assert seen == [("wait", HOST), ("observe", HOST, 403)]


# ---- PublicData.nse_json ---------------------------------------------------------------------------------------


class Reply:
    def __init__(self, status, text="x", payload=None):
        self.status_code, self.text, self.payload = status, text, payload or {"ok": 1}

    def json(self):
        return self.payload

    def raise_for_status(self):
        raise RuntimeError(f"HTTP {self.status_code}")


def client(monkeypatch, replies):
    sleeps, calls = [], []
    monkeypatch.setattr(public.time, "sleep", sleeps.append)
    data = public.PublicData()
    queue = list(replies)

    def get(url, **kw):
        calls.append(url)
        return Reply(200) if url.endswith("/option-chain") else queue.pop(0)  # the warm-up page always answers

    data.session = type("S", (), {"get": staticmethod(get)})()
    return data, sleeps, calls


def test_success_pauses_point_four_seconds_after(monkeypatch):
    data, sleeps, _ = client(monkeypatch, [Reply(200)])
    assert data.nse_json("/api/x") == {"ok": 1} and sleeps == [0.4]


def test_failures_warm_up_and_wait_1_5_then_3_0_then_stop_after_three_tries(monkeypatch):
    data, sleeps, calls = client(monkeypatch, [Reply(403)] * 3)
    with pytest.raises(RuntimeError, match="HTTP 403"):
        data.nse_json("/api/x")
    assert sleeps == [1.5, 3.0, 4.5]  # the last wait comes before the final error
    assert [u for u in calls if u.endswith("/api/x")] == [public.NSE + "/api/x"] * 3
    assert sum(u.endswith("/option-chain") for u in calls) == 1  # warmed once only


def test_recovery_on_the_second_try(monkeypatch):
    data, sleeps, _ = client(monkeypatch, [Reply(403), Reply(200)])
    assert data.nse_json("/api/x") == {"ok": 1} and sleeps == [1.5, 0.4]


def test_an_empty_200_counts_as_a_failure(monkeypatch):
    data, sleeps, _ = client(monkeypatch, [Reply(200, text="  "), Reply(200)])
    assert data.nse_json("/api/x") == {"ok": 1} and sleeps == [1.5, 0.4]


def test_every_paced_session_in_the_process_shares_one_pacer_and_so_one_pause():
    from fno.shared import http_pacing

    first, second = PacedSession(), PacedSession()
    assert first.pacer is second.pacer is http_pacing.SHARED_PACER
    assert PacedSession(RequestPacer()).pacer is not http_pacing.SHARED_PACER  # an explicit pacer is its own


def test_the_pacers_default_spacing_table_is_one_second_for_both_nse_hosts():
    from fno.shared.http_pacing import DEFAULT_SPACING_SECONDS, HOST_SPACING_SECONDS

    assert HOST_SPACING_SECONDS == {"www.nseindia.com": 1.0, "nsearchives.nseindia.com": 1.0}
    assert DEFAULT_SPACING_SECONDS == 1.0


def test_spacing_holds_across_threads():
    import threading
    import time

    p = RequestPacer(spacing={HOST: 0.05})
    starts, lock = [], threading.Lock()

    def work():
        p.wait_turn(HOST)
        with lock:
            starts.append(time.monotonic())

    threads = [threading.Thread(target=work) for _ in range(6)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    starts.sort()
    assert min(b - a for a, b in zip(starts, starts[1:])) >= 0.04


def test_a_403_is_retried_after_a_cookie_warm_up_because_nse_refuses_the_first_call(monkeypatch):
    data, sleeps, calls = client(monkeypatch, [Reply(403), Reply(200)])
    assert data.nse_json("/api/x") == {"ok": 1}
    assert calls == [public.NSE + "/api/x", public.NSE + "/option-chain", public.NSE + "/api/x"]  # refused, warmed, ok


def test_every_non_200_is_retried_the_same_way_even_a_404_or_a_503(monkeypatch):
    for status in (404, 429, 500, 503):
        data, sleeps, calls = client(monkeypatch, [Reply(status), Reply(200)])
        assert data.nse_json("/api/x") == {"ok": 1} and sleeps == [1.5, 0.4], status


def test_a_warm_up_failure_is_ignored_and_the_warm_up_happens_once(monkeypatch):
    import requests

    sleeps, calls = [], []
    monkeypatch.setattr(public.time, "sleep", sleeps.append)
    data = public.PublicData()
    queue = [Reply(403), Reply(403), Reply(200)]

    def get(url, **kw):
        calls.append(url)
        if url.endswith("/option-chain"):
            raise requests.ConnectionError("warm-up down")
        return queue.pop(0)

    data.session = type("S", (), {"get": staticmethod(get)})()
    assert data.nse_json("/api/x") == {"ok": 1}
    assert sum(u.endswith("/option-chain") for u in calls) == 1 and sleeps == [1.5, 3.0, 0.4]


def test_the_pacer_sees_the_warm_up_so_a_403_then_a_warm_200_does_not_count_two_in_a_row():
    p = RequestPacer()
    p.observe(HOST, 403)  # the refused first call
    p.observe(HOST, 200)  # the warm-up page answers
    p.observe(HOST, 403)
    p.wait_turn(HOST)  # still not paused: the 200 reset the count
