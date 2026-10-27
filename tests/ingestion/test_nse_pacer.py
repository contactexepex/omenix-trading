"""Story R1b: the NSE pacer on the shared resilience layer. The old pacer's behaviour is pinned in
`tests/characterization/`; here is what is new: the single probe after a pause, the threads that wait for it, the
answers that close or re-open the host, one pacer per process, and the hosts kept apart. Real threads, a fake clock for
the pause and real (tiny) spacing, so nothing waits long."""

from __future__ import annotations

import threading
import time

import pytest
import requests

from fno.shared import http_pacing
from fno.shared.http_pacing import PacedSession, SourceCoolingOff
from fno.shared.nse_pacer import NsePacer

WWW, ARCHIVES = "www.nseindia.com", "nsearchives.nseindia.com"


BOUND = 10.0  # seconds: a regression that blocks must fail a test in seconds, not hang the suite


def run_bounded(call, bound=BOUND):
    """Runs `call` on a daemon thread and fails the test if it has not finished in `bound` seconds (a blocked wait would
    otherwise hang pytest); returns the call's exception, or None."""
    caught = []

    def target():
        try:
            call()
        except BaseException as exc:  # noqa: BLE001
            caught.append(exc)

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    thread.join(bound)
    assert not thread.is_alive(), "the call is still blocked"
    return caught[0] if caught else None


class Pause:
    """A pacer whose host has just been refused twice and whose 15 minutes are over: the next request is the probe."""

    def __init__(self, probe_wait=5.0, spacing=0.05, sleep=time.sleep):
        self.now = [1000.0]
        self.pacer = NsePacer(spacing={WWW: spacing, ARCHIVES: spacing}, clock=lambda: self.now[0],
                              sleep=sleep, probe_wait_seconds=probe_wait)  # fmt: skip
        self.pacer.wait_turn(WWW)
        self.pacer.observe(WWW, 403)
        self.pacer.wait_turn(WWW)
        self.pacer.observe(WWW, 403)
        with pytest.raises(SourceCoolingOff):
            self.pacer.wait_turn(WWW)
        self.now[0] += 901


def three_threads(pause, probe_answer):
    """Three threads each ask for a turn; the first through is the probe and answers after a moment. Returns what each
    got ('go' with the time it started, or 'refused') and the number that started before the probe was answered."""
    started, outcomes, lock = [], {}, threading.Lock()
    answered = threading.Event()
    before_answer = []

    def work(name):
        try:
            pause.pacer.wait_turn(WWW)
        except SourceCoolingOff:
            with lock:
                outcomes[name] = "refused"
            return
        with lock:
            started.append(time.monotonic())
            outcomes[name] = "go"
            first = len(started) == 1 and not answered.is_set()
            before_answer.append(not answered.is_set())
        if first:
            time.sleep(0.2)  # the probe request is in flight
            probe_answer()
            answered.set()
        else:
            pause.pacer.observe(WWW, 200)

    threads = [threading.Thread(target=work, args=(n,), daemon=True) for n in "abc"]
    for t in threads:
        t.start()
    for t in threads:
        t.join(BOUND)
        assert not t.is_alive(), "a thread is still blocked waiting for the probe"
    return outcomes, sorted(started), sum(before_answer)


def test_after_the_pause_one_probe_goes_alone_and_a_good_answer_lets_the_others_through_one_spacing_apart():
    """Deterministic (no observed timing): the limit on waiting is far beyond the join bound, so threads that are not
    released by the probe's answer fail as 'still blocked'; and the waits the limiter hands the released threads are
    read from a recording sleep on the frozen clock, not measured after they wake."""
    waits, lock = [], threading.Lock()

    def record(seconds):
        with lock:
            waits.append(seconds)

    pause = Pause(probe_wait=100 * BOUND, sleep=record)
    waits.clear()  # the set-up's own spacing waits
    outcomes, _, before = three_threads(pause, lambda: pause.pacer.observe(WWW, 200))
    assert list(outcomes.values()) == ["go"] * 3
    assert before == 1  # only the probe had started when it was answered
    assert sorted(waits) == pytest.approx([0.05, 0.10])  # the probe's slot is free; the others one spacing apart


def test_a_refused_probe_refuses_all_three_and_only_one_request_was_sent():
    pause = Pause()
    outcomes, started, _ = three_threads(pause, lambda: pause.pacer.observe(WWW, 403))
    assert sorted(outcomes.values()) == ["go", "refused", "refused"] and len(started) == 1


def test_a_429_probe_also_reopens():
    pause = Pause()
    three_threads(pause, lambda: pause.pacer.observe(WWW, 429))
    with pytest.raises(SourceCoolingOff, match="30 minutes"):  # doubled
        pause.pacer.wait_turn(WWW)


def test_a_probe_answered_with_a_5xx_or_a_404_closes_the_host():
    for status in (503, 404, 500):
        pause = Pause()
        outcomes, _, _ = three_threads(pause, lambda s=status, p=pause: p.pacer.observe(WWW, s))
        assert list(outcomes.values()) == ["go"] * 3, status


def test_a_probe_with_no_answer_closes_the_host_as_the_old_pacer_left_the_door_open():
    pause = Pause()
    outcomes, _, _ = three_threads(pause, lambda: pause.pacer.unanswered(WWW))
    assert list(outcomes.values()) == ["go"] * 3
    pause.pacer.wait_turn(WWW)  # still open afterwards


def test_a_waiter_gives_up_on_a_probe_that_never_answers_and_goes_ahead():
    pause = Pause(probe_wait=0.2)
    pause.pacer.wait_turn(WWW)  # this is the probe; it never answers
    began = time.monotonic()
    assert run_bounded(lambda: pause.pacer.wait_turn(WWW)) is None  # a waiter: bounded, then it proceeds as normal
    assert time.monotonic() - began >= 0.15  # it really waited; that it finished at all is run_bounded's check
    pause.pacer.wait_turn(WWW)  # and the host is closed afterwards (a half-open host would block again)


def test_a_probe_that_raises_releases_the_waiters(monkeypatch):
    pause = Pause(probe_wait=100 * BOUND)  # only the failed probe can release the waiter, not the limit on waiting

    def boom(self, method, url, *a, **k):
        time.sleep(0.2)
        raise requests.ConnectionError("down")

    monkeypatch.setattr("requests.Session.request", boom)
    probe = PacedSession(pause.pacer)
    errors = []

    def run_probe():
        try:
            probe.get(f"https://{WWW}/x")
        except requests.ConnectionError as exc:
            errors.append(exc)

    thread = threading.Thread(target=run_probe, daemon=True)
    thread.start()
    time.sleep(0.05)  # the probe is in flight
    assert run_bounded(lambda: pause.pacer.wait_turn(WWW)) is None  # released by the failed probe
    thread.join(BOUND)
    assert not thread.is_alive() and len(errors) == 1


def test_the_hosts_are_kept_apart():
    pause = Pause()
    pause.pacer.wait_turn(ARCHIVES)  # the other host was never refused
    pause.pacer.observe(ARCHIVES, 403)
    pause.pacer.wait_turn(ARCHIVES)
    pause.pacer.wait_turn(WWW)  # the probe on the refused host is not held up by the other
    pause.pacer.observe(WWW, 200)


def test_every_session_in_the_process_shares_one_pacer_so_one_pause():
    first, second = PacedSession(), PacedSession()
    assert first.pacer is second.pacer is http_pacing.SHARED_PACER


def test_a_pause_reaches_callers_as_source_cooling_off_with_the_old_message():
    pacer = NsePacer(spacing={WWW: 0.0}, clock=lambda: 0.0)
    pacer.wait_turn(WWW)
    pacer.observe(WWW, 403)
    pacer.wait_turn(WWW)
    pacer.observe(WWW, 429)
    with pytest.raises(SourceCoolingOff) as paused:
        pacer.wait_turn(WWW)
    assert str(paused.value) == f"{WWW} refused requests (HTTP 429); not calling it for 15 minutes"
    assert isinstance(paused.value, requests.RequestException)


def test_a_thread_that_loses_the_race_to_become_the_probe_waits_instead_of_being_refused():
    """All three threads pass the 'is a probe out?' look before any of them asks leave to call: two of them then meet
    a half-open host and must wait for the probe, not be refused (the race the plain test above rarely hits)."""
    pause = Pause()
    looked = threading.Barrier(3, timeout=5)
    original, seen = pause.pacer._wait_for_probe, threading.local()

    def wait_for_probe(state):
        original(state)
        if not getattr(seen, "done", False):
            seen.done = True
            looked.wait()  # every thread has now looked, none has asked yet

    pause.pacer._wait_for_probe = wait_for_probe
    outcomes, _, _ = three_threads(pause, lambda: pause.pacer.observe(WWW, 200))
    assert list(outcomes.values()) == ["go"] * 3


def test_the_live_archive_policy_waits_between_the_old_table_and_a_quarter_more(http_fakes):
    from datetime import date

    from fno.ingestion.storage.raw_source import NseDailyFoSource, RawSourceUnavailable

    waits = []
    reply = http_fakes.Response(status_code=503)
    session = http_fakes.Session(routes=reply)
    source = NseDailyFoSource(session, sleep=waits.append)  # the default policy, real jitter
    with pytest.raises(RawSourceUnavailable):
        source.fetch(NseDailyFoSource.path_for(date(2026, 10, 12)))
    assert len(waits) == 3
    for wait, floor in zip(waits, (5, 15, 45)):
        assert floor <= wait <= floor * 1.25


def test_the_old_pacer_and_retry_table_are_gone_from_the_code():
    from pathlib import Path

    root = Path(__file__).resolve().parents[2] / "fno"
    text = "\n".join(p.read_text("utf-8") for p in root.rglob("*.py") if "resilience" not in p.parts)
    assert "class RequestPacer" not in text and "RETRY_WAITS = (5, 15, 45)" not in text


def test_a_thread_refused_the_instant_the_host_opens_gets_the_whole_message():
    pacer = NsePacer(spacing={WWW: 0.0}, clock=lambda: 0.0)
    pacer.wait_turn(WWW)
    pacer.observe(WWW, 403)
    pacer.wait_turn(WWW)
    state, messages = pacer._host(WWW), []
    opens = state.breaker.record_refusal

    def opens_then_another_thread_asks():
        opens()
        try:
            pacer.wait_turn(WWW)  # in the window between the host opening and observe() returning
        except SourceCoolingOff as refused:
            messages.append(str(refused))

    state.breaker.record_refusal = opens_then_another_thread_asks
    pacer.observe(WWW, 429)
    assert messages == [f"{WWW} refused requests (HTTP 429); not calling it for 15 minutes"]
