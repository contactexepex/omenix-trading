"""Story R1b2: the pacer's breakers are remembered between runs (real UTC, a shared log), alert once per transition, and
a live-window command keeps one attempt inside a carried-over cool-down. Real threads for the waiters, bounded."""

from __future__ import annotations

import threading
from datetime import UTC, datetime, timedelta

import pytest

from fno.shared.http_pacing import SourceCoolingOff
from fno.shared.nse_pacer import NsePacer
from fno.shared.resilience.transition_log import LayeredLog, TransitionLog

HOST = "www.nseindia.com"
T0 = datetime(2026, 10, 27, 9, 0, tzinfo=UTC)
BOUND = 10.0


class Wall:
    def __init__(self, at=T0):
        self.at = at

    def __call__(self):
        return self.at

    def advance(self, **kw):
        self.at += timedelta(**kw)


class Spy:
    def __init__(self):
        self.sent = []

    def send(self, text):
        self.sent.append(text)
        return "spy"


def process(tmp_path, wall, monotonic_origin, live=False, alerts=None):
    """A new process: its own monotonic clock (a different origin each time), the shared files."""
    pacer = NsePacer(
        spacing={HOST: 0.0}, clock=lambda: monotonic_origin, wall_clock=wall, probe_wait_seconds=5.0
    )  # fmt: skip
    committed, local = tmp_path / "paced-hosts.csv", tmp_path / ".run" / f"run{monotonic_origin}.csv"
    pacer.attach(LayeredLog(committed, local), alerts, live_window=live)
    return pacer


def refused_twice(pacer):
    for _ in range(2):
        pacer.wait_turn(HOST)
        pacer.observe(HOST, 403)


def merge(tmp_path):
    """What the last workflow step does: the run-local rows join the committed file."""
    committed = tmp_path / "paced-hosts.csv"
    for local in sorted((tmp_path / ".run").glob("*.csv")):
        TransitionLog(committed).path.parent.mkdir(parents=True, exist_ok=True)
        rows = local.read_text().splitlines()
        existing = committed.read_text().splitlines() if committed.is_file() else rows[:1]
        committed.write_text("\n".join([*existing, *[r for r in rows[1:] if r not in existing]]) + "\n")
        local.unlink()


def test_a_pause_is_restored_in_the_next_process_by_utc_whatever_its_monotonic_clock_says(tmp_path):
    wall = Wall()
    refused_twice(process(tmp_path, wall, monotonic_origin=1_000.0))
    merge(tmp_path)
    wall.advance(minutes=10)
    later = process(tmp_path, wall, monotonic_origin=9_999_999.0)  # a different monotonic origin
    with pytest.raises(SourceCoolingOff, match=r"refused in an earlier run; not calling it for 5 more minutes"):
        later.wait_turn(HOST)
    wall.advance(minutes=6)  # the 15 minutes are over: the next request is the probe
    later.wait_turn(HOST)
    later.observe(HOST, 200)
    later.wait_turn(HOST)  # and the host is closed again


def test_a_closed_or_missing_history_is_closed(tmp_path):
    process(tmp_path, Wall(), 1.0).wait_turn(HOST)  # no file at all
    wall = Wall()
    refused_twice(process(tmp_path, wall, 2.0))
    merge(tmp_path)
    wall.advance(minutes=16)
    prober = process(tmp_path, wall, 3.0)
    prober.wait_turn(HOST)  # the probe
    prober.observe(HOST, 200)  # closes: a `closed` row
    merge(tmp_path)
    process(tmp_path, wall, 4.0).wait_turn(HOST)  # the last row is closed: an ordinary call
    assert (tmp_path / "paced-hosts.csv").read_text().splitlines()[-1].split(",")[2] == "closed"


def test_one_alert_per_transition_and_none_for_a_failure_that_does_not_open(tmp_path):
    alerts, wall = Spy(), Wall()
    pacer = process(tmp_path, wall, 1.0, alerts=alerts)
    pacer.wait_turn(HOST)
    pacer.observe(HOST, 403)  # one refusal: no transition
    pacer.wait_turn(HOST)
    pacer.observe(HOST, 200)  # reset
    assert alerts.sent == []
    refused_twice(pacer)  # opens: one alert
    assert len(alerts.sent) == 1 and "OPEN" in alerts.sent[0] and HOST in alerts.sent[0]
    wall.advance(minutes=16)
    pacer.wait_turn(HOST)
    pacer.observe(HOST, 200)  # the probe closes it: one more
    assert len(alerts.sent) == 2 and "closed again" in alerts.sent[1]
    assert not any("token" in s.lower() for s in alerts.sent)  # no value, only the host and the minutes


def test_a_healthy_run_writes_no_file(tmp_path):
    pacer = process(tmp_path, Wall(), 1.0)
    for _ in range(5):
        pacer.wait_turn(HOST)
        pacer.observe(HOST, 200)
    assert list(tmp_path.rglob("*.csv")) == []


# ---- the live-window rule ----------------------------------------------------------------------------------


def opened_in_an_earlier_run(tmp_path, wall):
    refused_twice(process(tmp_path, wall, 1.0))
    merge(tmp_path)
    wall.advance(minutes=5)  # still inside the 15 minutes


def test_an_ordinary_command_is_refused_without_a_request_inside_the_carried_over_cool_down(tmp_path):
    wall = Wall()
    opened_in_an_earlier_run(tmp_path, wall)
    with pytest.raises(SourceCoolingOff):
        process(tmp_path, wall, 2.0, live=False).wait_turn(HOST)


def test_a_live_command_sends_one_probe_and_the_other_threads_wait_for_it(tmp_path):
    wall = Wall()
    opened_in_an_earlier_run(tmp_path, wall)
    pacer = process(tmp_path, wall, 2.0, live=True)
    sent, outcomes, lock = [], [], threading.Lock()

    def work():
        try:
            pacer.wait_turn(HOST)
        except SourceCoolingOff:
            with lock:
                outcomes.append("refused")
            return
        with lock:
            sent.append(1)
            first = len(sent) == 1
            outcomes.append("go")
        if first:
            threading.Event().wait(0.2)  # the probe is in flight
            assert len(sent) == 1  # nobody else started meanwhile
            pacer.observe(HOST, 200)

    threads = [threading.Thread(target=work, daemon=True) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(BOUND)
        assert not t.is_alive()
    assert outcomes == ["go"] * 3


def test_a_refused_live_probe_reopens_for_twice_as_long_and_is_forced_only_once_per_process(tmp_path):
    wall = Wall()
    opened_in_an_earlier_run(tmp_path, wall)
    live = process(tmp_path, wall, 2.0, live=True)
    live.wait_turn(HOST)  # the forced probe
    live.observe(HOST, 429)  # refused: re-opened, doubled
    with pytest.raises(SourceCoolingOff):  # not forced a second time in this process
        live.wait_turn(HOST)
    merge(tmp_path)
    with pytest.raises(SourceCoolingOff, match="30 more minutes"):  # an archive run later sees the doubled pause
        process(tmp_path, wall, 3.0, live=False).wait_turn(HOST)


def test_two_overlapping_live_processes_may_each_force_one_probe(tmp_path):
    wall = Wall()
    opened_in_an_earlier_run(tmp_path, wall)
    a, b = process(tmp_path, wall, 2.0, live=True), process(tmp_path, wall, 3.0, live=True)
    a.wait_turn(HOST)
    b.wait_turn(HOST)  # each read the log at its start, so each gets its one probe
