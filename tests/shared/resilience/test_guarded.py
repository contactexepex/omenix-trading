"""Retry policy plus breaker together, NSE-like and Drive-like classifiers, a spy source that counts requests."""

import pytest

from fno.shared.resilience.breaker import BreakerSettings, CircuitBreaker, State
from fno.shared.resilience.guarded import GuardedCall
from fno.shared.resilience.outcomes import Deferred, Outcome, Verdict
from fno.shared.resilience.retry import RetryPolicy
from fno.shared.resilience.settings import settings_for
from tests.shared.resilience.fakes import FakeClock, SpyAlerts, WallClock, floor_jitter


class Source:
    """Answers with a scripted sequence of statuses (None raises a timeout); counts every request."""

    def __init__(self, *statuses):
        self.statuses, self.requests = list(statuses), 0

    def __call__(self):
        self.requests += 1
        status = self.statuses.pop(0) if self.statuses else 200
        if status is None:
            raise TimeoutError("slow")
        return status


def nse_classify(status, error):
    if error is not None:
        return Verdict(Outcome.RETRY, answered=False)  # no answer: nothing to count, the run of refusals stays
    if status == 429:
        return Verdict(Outcome.RETRY, counts=True)
    if status == 403:
        return Verdict(Outcome.BLOCK, counts=True)
    if status == 404:
        return Verdict(Outcome.PERMANENT)
    if status >= 500:
        return Verdict(Outcome.RETRY)
    return Verdict(Outcome.OK)


def drive_classify(status, error):
    if error is not None or status >= 500 or status == 403:  # Drive's 403 is a rate limit: retried, not a block
        return Verdict(Outcome.RETRY, answered=error is None)
    return Verdict(Outcome.OK)


def guarded(source="nse", alerts=None):
    s = settings_for(source)
    clock, wall = FakeClock(), WallClock()
    breaker = CircuitBreaker(source, s.breaker, wall, alerts=alerts)
    return (
        GuardedCall(source, RetryPolicy(s.retry, clock.sleep, clock, floor_jitter), breaker, alerts),
        breaker,
        wall,
        clock,
    )


def test_a_good_answer_passes_through_with_the_breaker_closed():
    call, breaker, _, _ = guarded()
    done = call.call(Source(200), nse_classify)
    assert done.outcome is Outcome.OK and breaker.state is State.CLOSED


def test_two_consecutive_429s_open_the_breaker_and_no_third_request_is_sent():
    call, breaker, _, clock = guarded()
    source = Source(429, 429, 200)
    done = call.call(source, nse_classify)
    assert (source.requests, breaker.state, done.outcome) == (2, State.OPEN, Outcome.EXHAUSTED)
    assert clock.slept == [5.0]  # one wait between the two, none into the pause
    with pytest.raises(Deferred):
        call.call(source, nse_classify)
    assert source.requests == 2  # the open breaker sent nothing


def test_a_429_then_a_good_answer_keeps_it_closed():
    call, breaker, _, _ = guarded()
    assert call.call(Source(429, 200), nse_classify).outcome is Outcome.OK
    assert breaker.state is State.CLOSED


def test_a_timeout_between_two_429s_does_not_reset_the_run_as_the_pacer_does_not_see_it():
    call, breaker, _, _ = guarded()
    source = Source(429, None, 429)
    call.call(source, nse_classify)
    assert breaker.state is State.OPEN and source.requests == 3


def test_a_404_never_counts_and_resets_the_run():
    call, breaker, _, _ = guarded()
    for _ in range(5):
        assert call.call(Source(404), nse_classify).outcome is Outcome.PERMANENT
    assert breaker.state is State.CLOSED
    call.call(Source(429, 404, 429, 200), nse_classify)  # 429, then a plain answer, then 429: not consecutive
    assert breaker.state is State.CLOSED


def test_an_nse_403_is_a_block_not_retried_and_the_second_opens_the_breaker():
    call, breaker, _, _ = guarded()
    source = Source(403, 403)
    first = call.call(source, nse_classify)
    assert (first.outcome, source.requests, breaker.state) == (Outcome.BLOCK, 1, State.CLOSED)
    call.call(source, nse_classify)
    assert breaker.state is State.OPEN


def test_the_probe_is_one_request_outside_the_retry_policy_and_a_failure_reopens_for_longer():
    call, breaker, wall, clock = guarded()
    call.call(Source(429, 429), nse_classify)
    wall.advance(900)
    source = Source(429, 429, 429)
    done = call.call(source, nse_classify)  # the probe: a 429 is a RETRY outcome, but it is not retried
    assert source.requests == 1 and done.tries == 1 and clock.slept == [5.0]
    assert (breaker.state, breaker.cool_down) == (State.OPEN, 1800.0)


def test_a_good_probe_closes_it_and_calls_resume():
    call, breaker, wall, _ = guarded()
    call.call(Source(429, 429), nse_classify)
    wall.advance(900)
    assert call.call(Source(200), nse_classify).outcome is Outcome.OK
    assert breaker.state is State.CLOSED
    assert call.call(Source(200), nse_classify).outcome is Outcome.OK


def test_a_probe_that_times_out_or_gets_a_5xx_is_a_failed_probe():
    for bad in (None, 500):
        call, breaker, wall, _ = guarded()
        call.call(Source(429, 429), nse_classify)
        wall.advance(900)
        call.call(Source(bad), nse_classify)
        assert breaker.state is State.OPEN, bad


def test_drive_rate_limit_403_is_retried_and_exhausted_calls_count_toward_its_breaker():
    alerts = SpyAlerts()
    call, breaker, _, _ = guarded("drive", alerts)
    first = Source(*[403] * 5)
    done = call.call(first, drive_classify)
    assert (first.requests, done.outcome) == (5, Outcome.EXHAUSTED)  # Drive's table: 4 waits, 5 tries
    assert len(alerts.sent) == 1 and "gave up after 5 tries" in alerts.sent[0]
    assert breaker.failures == 1 and breaker.state is State.CLOSED


def test_drive_opens_after_five_exhausted_calls_with_one_alert_each_for_exhaustion_and_one_for_the_open():
    alerts = SpyAlerts()
    call, breaker, _, _ = guarded("drive", alerts)
    for _ in range(5):
        call.call(Source(*[403] * 5), drive_classify)
    assert breaker.state is State.OPEN and len(alerts.sent) == 6  # 5 exhaustion lines + 1 breaker-open line


def test_a_deferred_call_makes_no_request_and_leaves_the_caller_nothing_to_write():
    call, breaker, _, _ = guarded()
    call.call(Source(429, 429), nse_classify)
    written = []
    source = Source(200)
    with pytest.raises(Deferred):
        written.append(call.call(source, nse_classify))
    assert source.requests == 0 and written == []


def test_the_exhaustion_of_a_call_the_breaker_already_stopped_is_not_counted_twice():
    call, breaker, _, _ = guarded()
    call.call(Source(429, 429), nse_classify)
    assert breaker.failures == 0  # count_exhausted is off for NSE: every 429 was already counted


def test_a_breaker_with_count_exhausted_off_does_not_count_exhausted_calls():
    s = settings_for("nse")
    assert s.breaker.count_exhausted is False and BreakerSettings(2, 1.0, 2.0).count_exhausted is True


def test_nse_a_404_between_two_403s_resets_the_run_of_refusals():
    call, breaker, _, _ = guarded()
    call.call(Source(403), nse_classify)  # one counted refusal, the call ends (BLOCK)
    call.call(Source(404), nse_classify)  # a plain answer ends the run, as RequestPacer.observe does today
    call.call(Source(403), nse_classify)
    assert breaker.state is State.CLOSED  # 403, 404, 403 is not two in a row


def test_nse_two_403s_in_a_row_open_it_so_the_reset_test_above_is_not_vacuous():
    call, breaker, _, _ = guarded()
    call.call(Source(403), nse_classify)
    call.call(Source(403), nse_classify)
    assert breaker.state is State.OPEN


def test_a_probe_answered_404_closes_the_breaker():
    call, breaker, wall, _ = guarded()
    breaker.record_refusal()
    breaker.record_refusal()
    wall.advance(901)
    done = call.call(Source(404), nse_classify)
    assert done.tries == 1 and breaker.state is State.CLOSED
