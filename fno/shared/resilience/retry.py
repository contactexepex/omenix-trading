"""The retry policy (story R1): retry only what is transient, wait at least as long as today's code does, spread the
retries upward with jitter, honour Retry-After, and stop at bounded attempts and total time.

Each source keeps its own per-attempt wait table as the FLOOR (NSE 5/15/45 s, Drive 2/8/30/60 s are today's numbers);
the wait before try n is `t_n + random(0, jitter * t_n)`, so never below today's. Full or equal jitter could wait
less than today's first wait and is deliberately not used. Time, sleep and randomness are injected, so tests are
deterministic."""

from __future__ import annotations

import random
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, TypeVar

from fno.shared.resilience.outcomes import Outcome, Verdict

T = TypeVar("T")


@dataclass(frozen=True)
class RetrySettings:
    waits: tuple[float, ...]  # the floor of the wait before retry 1, 2, ...; len(waits) + 1 tries at most
    cap_seconds: float  # longest jittered wait; checked >= (1 + jitter) x the largest floor, so no clipping is needed
    retry_after_ceiling_seconds: (
        float  # a Retry-After above this stops the call (the source is blocking, not hiccuping)
    )
    max_total_seconds: float  # the call gives up when waiting would pass this
    jitter: float = 1.0  # a wait is its floor plus up to `jitter` x the floor (NSE: 0.25, to keep worst cases close)

    def __post_init__(self) -> None:
        if not self.waits or any(w <= 0 for w in self.waits):
            raise ValueError("waits must be a non-empty list of positive seconds")
        if self.jitter < 0:
            raise ValueError("jitter must not be negative")
        longest = (1 + self.jitter) * max(self.waits)
        if self.cap_seconds < longest:
            raise ValueError(f"cap_seconds {self.cap_seconds} is below the longest jittered wait {longest}")

    @property
    def max_attempts(self) -> int:
        return len(self.waits) + 1


@dataclass
class Attempted(Generic[T]):
    result: T | None
    error: Exception | None
    outcome: Outcome
    tries: int
    waited_seconds: float
    reason: str = ""  # why a call ended EXHAUSTED


class RetryPolicy:
    def __init__(self, settings: RetrySettings, sleep: Callable[[float], None] = time.sleep,
                 clock: Callable[[], float] = time.monotonic,
                 uniform: Callable[[float, float], float] = random.uniform):  # fmt: skip
        self.settings, self.sleep, self.clock, self.uniform = settings, sleep, clock, uniform

    def wait_before(self, retry_number: int, retry_after: float | None = None) -> float:
        """Seconds to wait before retry `retry_number` (1-based): the table's floor plus upward jitter; Retry-After is a
        floor too."""
        floor = self.settings.waits[retry_number - 1]
        wait = floor + self.uniform(0.0, floor * self.settings.jitter)
        return max(wait, retry_after) if retry_after else wait

    def run(self, attempt: Callable[[], T], classify: Callable[[T | None, Exception | None], Verdict],
            observe: Callable[[Verdict], bool] | None = None) -> Attempted[T]:  # fmt: skip
        """Calls `attempt` until it ends OK, PERMANENT or BLOCK, or the retries run out. `observe(verdict)` sees every
        answer (the breaker counts them) and returns True to stop at once, before any further wait."""
        started, tries, waited = self.clock(), 0, 0.0
        while True:
            tries += 1
            result, error = None, None
            try:
                result = attempt()
            except Exception as exc:  # the classifier decides what an exception means  # noqa: BLE001
                error = exc
            verdict = classify(result, error)
            if observe is not None and observe(verdict):
                return Attempted(result, error, Outcome.EXHAUSTED, tries, waited, "stopped by the circuit breaker")
            if verdict.outcome is not Outcome.RETRY:
                return Attempted(result, error, verdict.outcome, tries, waited)
            reason = self._give_up_reason(verdict, tries, started, waited)
            if reason:
                return Attempted(result, error, Outcome.EXHAUSTED, tries, waited, reason)
            wait = self.wait_before(tries, verdict.retry_after)
            if self.clock() - started + wait > self.settings.max_total_seconds:
                return Attempted(result, error, Outcome.EXHAUSTED, tries, waited, "total time limit")
            self.sleep(wait)
            waited += wait

    def _give_up_reason(self, verdict: Verdict, tries: int, started: float, waited: float) -> str:
        if tries >= self.settings.max_attempts:
            return "attempt limit"
        if verdict.retry_after is not None and verdict.retry_after > self.settings.retry_after_ceiling_seconds:
            return "Retry-After above the ceiling"
        return ""
