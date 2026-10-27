import random

import pytest

from fno.shared.resilience.outcomes import Outcome, Verdict
from fno.shared.resilience.retry import RetryPolicy, RetrySettings
from fno.shared.resilience.settings import settings_for
from tests.shared.resilience.fakes import FakeClock, floor_jitter, top_jitter

TABLES = {"nse": (5.0, 15.0, 45.0), "drive": (2.0, 8.0, 30.0, 60.0)}


def policy(source="nse", uniform=floor_jitter, clock=None, settings=None):
    clock = clock or FakeClock()
    return RetryPolicy(settings or settings_for(source).retry, clock.sleep, clock, uniform), clock


def always(outcome, retry_after=None):
    return lambda result, error: Verdict(outcome, retry_after)


def test_ok_returns_at_once_without_waiting():
    p, clock = policy()
    done = p.run(lambda: "data", always(Outcome.OK))
    assert (done.result, done.outcome, done.tries, clock.slept) == ("data", Outcome.OK, 1, [])


@pytest.mark.parametrize("outcome", [Outcome.PERMANENT, Outcome.BLOCK])
def test_permanent_and_block_are_never_retried(outcome):
    p, clock = policy()
    done = p.run(lambda: "x", always(outcome))
    assert (done.outcome, done.tries, clock.slept) == (outcome, 1, [])


def test_an_exception_is_given_to_the_classifier_and_retried_when_it_says_so():
    p, clock = policy()
    calls = []

    def attempt():
        calls.append(1)
        if len(calls) < 3:
            raise ConnectionError("down")
        return "ok"

    done = p.run(attempt, lambda r, e: Verdict(Outcome.RETRY if e else Outcome.OK))
    assert (done.result, done.tries, len(clock.slept)) == ("ok", 3, 2)


@pytest.mark.parametrize("source", sorted(TABLES))
def test_the_least_jitter_waits_exactly_todays_table_and_the_most_waits_floor_plus_its_jitter_fraction(source):
    table = TABLES[source]
    low, low_clock = policy(source, floor_jitter)
    low.run(lambda: 0, always(Outcome.RETRY))
    high, high_clock = policy(source, top_jitter)
    high.run(lambda: 0, always(Outcome.RETRY))
    assert low_clock.slept == list(table)
    top = 1 + settings_for(source).retry.jitter
    assert high_clock.slept == pytest.approx([top * t for t in table])


@pytest.mark.parametrize("source", sorted(TABLES))
def test_no_realized_wait_is_ever_below_todays_wait_for_that_attempt(source):
    table = TABLES[source]
    for seed in range(200):
        p, clock = policy(source, random.Random(seed).uniform)
        p.run(lambda: 0, always(Outcome.RETRY))
        assert all(t <= waited <= 2 * t for waited, t in zip(clock.slept, table, strict=True)), (seed, clock.slept)


def test_tries_are_bounded_by_the_table_length_plus_one():
    for source, table in TABLES.items():
        p, _ = policy(source)
        done = p.run(lambda: 0, always(Outcome.RETRY))
        assert (done.outcome, done.tries, done.reason) == (Outcome.EXHAUSTED, len(table) + 1, "attempt limit")


def test_retry_after_is_a_floor_for_the_wait():
    p, clock = policy()
    p.run(lambda: 0, always(Outcome.RETRY, retry_after=40))
    assert clock.slept == [40, 40, 45.0]  # Retry-After lifts a short wait, never shortens a longer one


def test_a_retry_after_above_the_ceiling_stops_the_call_with_no_wait():
    p, clock = policy()
    done = p.run(lambda: 0, always(Outcome.RETRY, retry_after=121))
    assert (done.outcome, done.tries, clock.slept) == (Outcome.EXHAUSTED, 1, [])
    assert "Retry-After" in done.reason


def test_a_retry_after_at_the_ceiling_is_honoured():
    p, clock = policy()
    p.run(lambda: 0, always(Outcome.RETRY, retry_after=120))
    assert clock.slept[0] == 120


def test_the_total_time_limit_stops_the_call_before_a_wait_that_would_pass_it():
    settings = RetrySettings(
        waits=(5.0, 15.0, 45.0), cap_seconds=90.0, retry_after_ceiling_seconds=120.0, max_total_seconds=10.0
    )
    p, clock = policy(settings=settings)
    done = p.run(lambda: 0, always(Outcome.RETRY))
    assert (done.outcome, done.reason, clock.slept) == (Outcome.EXHAUSTED, "total time limit", [5.0])


def test_observe_can_stop_the_retries_before_any_wait():
    p, clock = policy()
    seen = []

    def observe(verdict):
        seen.append(verdict)
        return len(seen) == 2

    done = p.run(lambda: 0, always(Outcome.RETRY), observe=observe)
    assert (done.tries, done.outcome, len(clock.slept)) == (2, Outcome.EXHAUSTED, 1)
    assert done.reason == "stopped by the circuit breaker"


def test_settings_refuse_a_cap_below_twice_the_largest_floor_and_empty_or_bad_waits():
    with pytest.raises(ValueError):
        RetrySettings(waits=(5.0, 45.0), cap_seconds=89.0, retry_after_ceiling_seconds=120.0, max_total_seconds=1.0)
    with pytest.raises(ValueError):
        RetrySettings(waits=(), cap_seconds=10.0, retry_after_ceiling_seconds=1.0, max_total_seconds=1.0)
    with pytest.raises(ValueError):
        RetrySettings(waits=(0.0,), cap_seconds=10.0, retry_after_ceiling_seconds=1.0, max_total_seconds=1.0)


def test_nse_and_drive_jitter_is_a_quarter():
    assert settings_for("nse").retry.jitter == 0.25 and settings_for("drive").retry.jitter == 0.25


def test_jitter_scales_the_random_part_and_a_cap_below_the_longest_jittered_wait_is_refused():
    seen = []

    def spy(low, high):
        seen.append((low, high))
        return low

    p, _ = policy("nse", spy)
    p.run(lambda: 0, always(Outcome.RETRY))
    assert seen == [(0.0, 5.0 * 0.25), (0.0, 15.0 * 0.25), (0.0, 45.0 * 0.25)]
    with pytest.raises(ValueError, match="longest jittered"):
        RetrySettings(waits=(10.0,), cap_seconds=12.0, retry_after_ceiling_seconds=1.0, max_total_seconds=1.0,
                      jitter=0.25)  # fmt: skip
    RetrySettings(waits=(10.0,), cap_seconds=12.5, retry_after_ceiling_seconds=1.0, max_total_seconds=1.0, jitter=0.25)
    with pytest.raises(ValueError, match="jitter"):
        RetrySettings(waits=(10.0,), cap_seconds=99.0, retry_after_ceiling_seconds=1.0, max_total_seconds=1.0,
                      jitter=-0.1)  # fmt: skip
