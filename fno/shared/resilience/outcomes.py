"""What one attempt at an external call turned out to be (story R1): the vocabulary the retry policy, the circuit
breaker and the callers share. A source's classifier turns its own answers (an HTTP status, an exception) into these."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Outcome(Enum):
    OK = "ok"
    RETRY = "retry"  # transient: worth another try after a wait
    PERMANENT = "permanent"  # never retried: not published (404), a parse or auth failure, a bad request
    BLOCK = "block"  # the source is refusing us: never retried
    EXHAUSTED = (
        "exhausted"  # a final result only: the retries ran out (attempts, total time, or a Retry-After too long)
    )


@dataclass(frozen=True)
class Verdict:
    """A classifier's answer for one attempt. `counts` says whether this answer counts toward the source's circuit
    breaker (NSE: every 403 and 429, as the pacer counts them today); any answer that does not count resets the run of
    consecutive refusals, as the pacer does."""

    outcome: Outcome
    retry_after: float | None = None  # seconds the source asked us to wait
    counts: bool = False
    answered: bool = True  # False for a timeout or dropped connection: no answer to count, so the run of refusals stays


class Deferred(RuntimeError):
    """The call was not made, or was given up: the caller writes nothing for it and the next scheduled run retries."""

    def __init__(self, source: str, reason: str):
        super().__init__(f"{source}: {reason}")
        self.source, self.reason = source, reason
