"""Retry policy and circuit breaker used together (story R1): the one place that decides how a call to an external
source is made. Closed breaker: the retry policy runs the call and every answer is shown to the breaker, which can stop
the retries at once (NSE's second consecutive 403/429). Cool-down over: a single probe, one request, no retries.
Open: the call is not made and the caller gets `Deferred` (it writes nothing; the next scheduled run retries)."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from fno.shared.alerts.sender import AlertSender
from fno.shared.resilience.breaker import Admission, CircuitBreaker, State
from fno.shared.resilience.outcomes import Deferred, Outcome, Verdict
from fno.shared.resilience.retry import Attempted, RetryPolicy

T = TypeVar("T")
ALERT_EXHAUSTED = "Omenix F&O: {source} gave up after {tries} tries ({reason}); the next run retries"


class GuardedCall:
    def __init__(self, source: str, policy: RetryPolicy, breaker: CircuitBreaker, alerts: AlertSender | None = None):
        self.source, self.policy, self.breaker, self.alerts = source, policy, breaker, alerts

    def call(self, attempt: Callable[[], T], classify: Callable[[T | None, Exception | None], Verdict]) -> Attempted[T]:
        if self.breaker.check() is Admission.PROBE:
            return self._probe(attempt, classify)
        done = self.policy.run(attempt, classify, observe=self._observe)
        if done.outcome is Outcome.EXHAUSTED:
            if self.breaker.settings.count_exhausted and self.breaker.state is State.CLOSED:
                self.breaker.record_refusal()
            if self.alerts:
                self.alerts.send(ALERT_EXHAUSTED.format(source=self.source, tries=done.tries, reason=done.reason))
        return done

    def _observe(self, verdict: Verdict) -> bool:
        """Shows each answer to the breaker; True stops the retries (it has just opened)."""
        if not verdict.answered:
            return False
        if verdict.counts:
            self.breaker.record_refusal()
            return self.breaker.state is not State.CLOSED
        # NSE: any plain answer ends the run of refusals (as the pacer does). A source that counts exhausted calls
        # (Drive) is reset only by a good answer, or its retries would wipe the count before the call gives up.
        if verdict.outcome is Outcome.OK or not self.breaker.settings.count_exhausted:
            self.breaker.record_other()
        return False

    def _probe(self, attempt, classify) -> Attempted:
        """Exactly one request, outside the retry policy (a retried probe would be several hits on a blocking host)."""
        result, error = None, None
        try:
            result = attempt()
        except Exception as exc:  # noqa: BLE001
            error = exc
        verdict = classify(result, error)
        if _probe_succeeded(verdict):
            self.breaker.record_other()
        else:
            self.breaker.record_refusal()
        return Attempted(result, error, verdict.outcome, 1, 0.0)


def _probe_succeeded(verdict: Verdict) -> bool:
    """The source answered and is not refusing: OK, or a plain answer such as 404 (it responded). A timeout, a 5xx or a
    refusal means the probe failed and the breaker opens again, for longer."""
    return verdict.answered and not verdict.counts and verdict.outcome in (Outcome.OK, Outcome.PERMANENT)


__all__ = ["Deferred", "GuardedCall"]
