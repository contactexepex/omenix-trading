import pytest

from fno.shared.resilience.breaker import Admission, BreakerSettings, CircuitBreaker, State
from fno.shared.resilience.outcomes import Deferred
from fno.shared.resilience.settings import settings_for
from fno.shared.resilience.transition_log import Transition, TransitionLog
from tests.shared.resilience.fakes import SpyAlerts, WallClock

SETTINGS = BreakerSettings(threshold=2, cool_down_seconds=900.0, cool_down_cap_seconds=3600.0)


def make(settings=SETTINGS, log=None, alerts=None, clock=None):
    clock = clock or WallClock()
    return CircuitBreaker("nse", settings, clock, log, alerts), clock


def test_a_new_breaker_is_closed_and_admits_calls():
    breaker, _ = make()
    assert breaker.state is State.CLOSED and breaker.check() is Admission.CALL


def test_it_opens_at_the_threshold_not_before():
    breaker, _ = make()
    breaker.record_refusal()
    assert breaker.state is State.CLOSED
    breaker.record_refusal()
    assert breaker.state is State.OPEN


def test_an_answer_that_is_not_a_counted_refusal_ends_the_run():
    breaker, _ = make()
    breaker.record_refusal()
    breaker.record_other()
    breaker.record_refusal()
    assert breaker.state is State.CLOSED  # 2 refusals, but not consecutive


def test_while_open_and_cooling_a_call_is_deferred_with_nothing_sent():
    breaker, clock = make()
    breaker.record_refusal()
    breaker.record_refusal()
    clock.advance(899)
    with pytest.raises(Deferred, match="circuit open"):
        breaker.check()


def test_after_the_cool_down_exactly_one_probe_is_admitted():
    breaker, clock = make()
    for _ in range(2):
        breaker.record_refusal()
    clock.advance(900)
    assert breaker.check() is Admission.PROBE
    assert breaker.state is State.HALF_OPEN
    with pytest.raises(Deferred, match="probe is already out"):
        breaker.check()


def test_a_good_probe_closes_it_and_resets_the_cool_down():
    breaker, clock = make()
    for _ in range(2):
        breaker.record_refusal()
    clock.advance(900)
    breaker.check()
    breaker.record_other()
    assert breaker.state is State.CLOSED and breaker.cool_down == 900.0
    assert breaker.check() is Admission.CALL


def test_a_failed_probe_reopens_for_twice_as_long_up_to_the_cap_and_a_close_resets_it():
    breaker, clock = make()
    for _ in range(2):
        breaker.record_refusal()
    expected = [1800.0, 3600.0, 3600.0]  # doubles, then stays at the cap
    for cool_down in expected:
        clock.advance(breaker.cool_down)
        assert breaker.check() is Admission.PROBE
        breaker.record_refusal()
        assert (breaker.state, breaker.cool_down) == (State.OPEN, cool_down)
    clock.advance(3600)
    breaker.check()
    breaker.record_other()
    assert breaker.cool_down == 900.0


def test_one_alert_per_open_and_per_close_and_none_for_the_half_open_step():
    alerts = SpyAlerts()
    breaker, clock = make(alerts=alerts)
    for _ in range(2):
        breaker.record_refusal()
    clock.advance(900)
    breaker.check()
    assert len(alerts.sent) == 1 and "OPEN" in alerts.sent[0]
    breaker.record_other()
    assert len(alerts.sent) == 2 and "closed again" in alerts.sent[1]


def test_transitions_not_calls_are_written_and_a_new_process_restores_an_open_breaker(tmp_path):
    log = TransitionLog(tmp_path / "nse.csv")
    breaker, clock = make(log=log)
    for _ in range(5):  # extra refusals while open write nothing
        breaker.record_refusal()
    assert [t.event for t in log.rows("nse")] == ["opened"]
    again, _ = make(log=log, clock=clock)  # a fresh process reading the same file
    assert again.state is State.OPEN
    with pytest.raises(Deferred):
        again.check()
    clock.advance(900)
    assert again.check() is Admission.PROBE


def test_a_closed_history_restores_closed_and_a_dangling_half_open_is_treated_as_open(tmp_path):
    log = TransitionLog(tmp_path / "nse.csv")
    breaker, clock = make(log=log)
    for _ in range(2):
        breaker.record_refusal()
    clock.advance(900)
    breaker.check()  # half_open written, process "dies" here
    died, _ = make(log=log, clock=clock)
    assert died.state is State.OPEN
    breaker.record_other()
    healed, _ = make(log=log, clock=clock)
    assert healed.state is State.CLOSED


def test_the_log_is_read_in_time_order_even_when_union_merged_out_of_order(tmp_path):
    log = TransitionLog(tmp_path / "nse.csv")
    clock = WallClock()
    later = Transition(clock.at, "nse", "closed", 900.0)
    clock.advance(-60)
    earlier = Transition(clock.at, "nse", "opened", 900.0)
    log.append(later)
    log.append(earlier)
    assert [t.event for t in log.rows("nse")] == ["opened", "closed"] and log.last("nse").event == "closed"
    assert log.rows("drive") == [] and TransitionLog(tmp_path / "none.csv").last("nse") is None


def test_settings_are_validated():
    for bad in [(0, 900.0, 3600.0), (2, 0.0, 3600.0), (2, 900.0, 899.0)]:
        with pytest.raises(ValueError):
            BreakerSettings(*bad)


def test_exactly_one_probe_among_concurrent_checks():
    import threading

    from fno.shared.resilience.breaker import Admission

    import time

    wall = WallClock()
    breaker = CircuitBreaker("nse", settings_for("nse").breaker, wall)
    breaker.record_refusal()
    breaker.record_refusal()
    wall.advance(901)

    def slow_clock():  # reading the time takes a moment, which is what lets unlocked threads interleave
        time.sleep(0.02)
        return wall()

    breaker.clock = slow_clock
    barrier, results = threading.Barrier(8), []

    def work():
        barrier.wait()
        try:
            results.append(breaker.check())
        except Deferred:
            results.append("deferred")

    threads = [threading.Thread(target=work) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert results.count(Admission.PROBE) == 1 and results.count("deferred") == 7
