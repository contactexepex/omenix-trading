"""One answer from a source and what it means for the pace (story MS-P0b section 3; judge 626): a 429 waits once on
NSE and stops Groww at once; every other 4xx, any unknown error and any answer that is not the expected JSON stop the
source for the day; a 5xx or a timeout is retried once."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum

TOO_MANY = 429
UNEXPECTED = "answer is not the expected JSON"


class Verdict(StrEnum):
    OK = "ok"
    RETRY_RATE = "retry_rate"
    RETRY_SERVER = "retry_server"
    STOP = "stop"


@dataclass(frozen=True)
class RawAnswer:
    """What a source adapter saw: the HTTP status (or the SDK error's code), whether it timed out or was rate-limited,
    the parsed payload and whether it has the expected shape. `error_name` is a class name only, never a message."""

    status: int | None = None
    payload: object = None
    shape_ok: bool = False
    rate_limited: bool = False
    timed_out: bool = False
    error_name: str = ""

    def sha256(self) -> str:
        return hashlib.sha256(json.dumps(self.payload, sort_keys=True, default=str).encode()).hexdigest()


def judge(answer: RawAnswer, first_429_stops: bool) -> tuple[Verdict, str]:
    """The verdict and, for a stop, its plain reason (a status or a class name, never a value)."""
    if answer.rate_limited or answer.status == TOO_MANY:
        return (Verdict.STOP, "HTTP 429") if first_429_stops else (Verdict.RETRY_RATE, "HTTP 429")
    if answer.timed_out or (answer.status is not None and 500 <= answer.status < 600):
        return Verdict.RETRY_SERVER, f"HTTP {answer.status}" if answer.status else "timeout"
    if answer.status is not None and 400 <= answer.status < 500:
        return Verdict.STOP, f"HTTP {answer.status}"
    if answer.error_name:
        return Verdict.STOP, answer.error_name  # an error we cannot place fails closed
    if not answer.shape_ok:
        return Verdict.STOP, UNEXPECTED
    return Verdict.OK, ""
