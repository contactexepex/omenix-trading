import pytest

from fno.shared.resilience.outcomes import Deferred
from fno.shared.resilience.rate_limit import MemoryLedger, RateLimit, RateSettings
from tests.shared.resilience.fakes import FakeClock


def limit(settings, ledger=None):
    clock = FakeClock()
    return RateLimit("src", settings, ledger, clock.sleep, clock), clock


def test_spacing_makes_the_second_call_wait_and_the_first_does_not():
    rate, clock = limit(RateSettings(min_spacing_seconds=1.0))
    rate.acquire()
    rate.acquire()
    rate.acquire()
    assert clock.slept == [1.0, 1.0]


def test_a_call_after_the_spacing_has_passed_does_not_wait():
    rate, clock = limit(RateSettings(min_spacing_seconds=1.0))
    rate.acquire()
    clock.now += 5
    rate.acquire()
    assert clock.slept == []


def test_the_per_minute_budget_makes_the_next_call_wait_for_the_window():
    rate, clock = limit(RateSettings(min_spacing_seconds=0.0, per_minute=3))
    for _ in range(3):
        rate.acquire()
    rate.acquire()  # the 4th inside a minute
    assert clock.slept == [60.0]


def test_the_per_day_budget_defers_without_counting_the_refused_call():
    rate, _ = limit(RateSettings(min_spacing_seconds=0.0, per_day=2))
    rate.acquire()
    rate.acquire()
    with pytest.raises(Deferred, match="daily budget"):
        rate.acquire()
    assert rate.ledger.used_today() == 2


def test_a_ledger_shared_between_processes_carries_the_day_across():
    ledger = MemoryLedger()  # stands for a persisted ledger read by two processes
    first, _ = limit(RateSettings(min_spacing_seconds=0.0, per_day=150), ledger)
    for _ in range(149):
        first.acquire()
    second, _ = limit(RateSettings(min_spacing_seconds=0.0, per_day=150), ledger)
    second.acquire()  # the 150th
    with pytest.raises(Deferred):
        second.acquire()  # the 151st, in a different "process"


def test_a_wait_longer_than_max_wait_is_a_deferral_not_a_sleep():
    rate, clock = limit(RateSettings(min_spacing_seconds=300.0, max_wait_seconds=120.0))
    rate.acquire()
    with pytest.raises(Deferred, match="rate limit"):
        rate.acquire()
    assert clock.slept == []
