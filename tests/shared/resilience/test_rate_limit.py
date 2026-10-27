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


# ---- a ledger on disk, and threads ------------------------------------------------------------------------------


def test_a_file_ledger_carries_the_day_across_two_instances_and_resets_on_the_next_ist_day(tmp_path):
    from datetime import UTC, datetime, timedelta

    from fno.shared.resilience.rate_limit import FileDayLedger

    clock = [datetime(2026, 10, 27, 4, 0, tzinfo=UTC)]  # 09:30 IST
    path = tmp_path / "nested" / "groww-sign-in.csv"
    first, second = FileDayLedger(path, lambda: clock[0]), FileDayLedger(path, lambda: clock[0])
    assert first.used_today() == 0  # no file yet
    rates = RateSettings(min_spacing_seconds=0.0, per_day=150)
    one = RateLimit("groww_sign_in", rates, first, lambda s: None, lambda: 0.0)
    for _ in range(150):
        one.acquire()
    other = RateLimit("groww_sign_in", rates, second, lambda s: None, lambda: 0.0)  # a new process, same file
    with pytest.raises(Deferred, match="daily budget"):
        other.acquire()
    clock[0] += timedelta(hours=14)  # 23:30 IST, still the same IST day
    assert second.used_today() == 150
    clock[0] += timedelta(hours=1)  # 00:30 IST next day
    assert second.used_today() == 0


def test_spacing_holds_across_threads():
    """Deterministic (a frozen clock; the sleeps the limiter asks for are the slots it handed out), so thread wake-up
    jitter under load cannot shrink an observed gap: 8 callers must be given 8 distinct slots, 0.05 s apart."""
    import threading
    import time

    asked, lock = [], threading.Lock()

    def record(seconds):
        with lock:
            asked.append(seconds)

    rate = RateLimit(
        "src", RateSettings(min_spacing_seconds=0.05, max_wait_seconds=10.0), sleep=record, clock=lambda: 0.0
    )
    decide = rate._next_start

    def slow_decide(now):  # deciding takes a moment, which is what lets unlocked threads interleave
        start = decide(now)
        time.sleep(0.01)
        return start

    rate._next_start = slow_decide
    threads = [threading.Thread(target=rate.acquire) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    # the first caller is free; unlocked, several callers would compute the same slot and ask for the same wait
    assert sorted(asked) == pytest.approx([0.05 * n for n in range(1, 8)])


def test_per_minute_budget_holds_across_threads():
    import threading

    starts, lock = [], threading.Lock()

    def record_sleep(seconds):  # the clock never moves, so each sleep is that call's reserved start
        with lock:
            starts.append(seconds)

    rate = RateLimit("src", RateSettings(min_spacing_seconds=0.0, per_minute=3, max_wait_seconds=500.0), None,
                     record_sleep, lambda: 0.0)  # fmt: skip
    threads = [threading.Thread(target=rate.acquire) for _ in range(9)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(starts) == [60.0] * 3 + [120.0] * 3  # three start at once (no sleep), three a minute on, three two
