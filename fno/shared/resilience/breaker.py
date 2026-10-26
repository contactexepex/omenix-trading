"""The circuit breaker (story R1), one per source: closed -> open after enough consecutive refusals, fail fast while
open and cooling, half-open with exactly ONE probe after the cool-down, closed again on a good answer.

Never looser than today's pacer: NSE opens at 2 consecutive refusals (`REFUSALS_BEFORE_PAUSE`) with a 15-minute
starting cool-down. New here: the cool-down DOUBLES on each re-open up to a cap and resets on a close, so a days-long
block is not probed by almost every scheduled run; the state survives a new process through the transition log; one
alert per transition goes to #fno-desk only. The probe is one request outside the retry policy (see `guarded.py`)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from fno.shared.alerts.sender import AlertSender
from fno.shared.models import now_utc
from fno.shared.resilience.outcomes import Deferred
from fno.shared.resilience.transition_log import CLOSED, HALF_OPEN, OPENED, REOPENED, Transition, TransitionLog


class State(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class Admission(Enum):
    CALL = "call"  # closed: an ordinary call, with the retry policy
    PROBE = "probe"  # half-open: exactly one request, no retries


@dataclass(frozen=True)
class BreakerSettings:
    threshold: int  # consecutive counted refusals that open it
    cool_down_seconds: float  # the first cool-down
    cool_down_cap_seconds: float  # the cool-down doubles on each re-open up to this
    count_exhausted: bool = True  # an exhausted call counts as one refusal (NSE counts each 403/429 instead)

    def __post_init__(self) -> None:
        if self.threshold < 1 or self.cool_down_seconds <= 0 or self.cool_down_cap_seconds < self.cool_down_seconds:
            raise ValueError("breaker needs threshold >= 1 and 0 < cool_down_seconds <= cool_down_cap_seconds")


ALERT_OPENED = "Omenix F&O: circuit breaker for {source} OPEN ({event}); no calls for {minutes:.0f} min, then one probe"
ALERT_CLOSED = "Omenix F&O: circuit breaker for {source} closed again; calls resume"


class CircuitBreaker:
    def __init__(self, source: str, settings: BreakerSettings, clock: Callable[[], datetime] = now_utc,
                 log: TransitionLog | None = None, alerts: AlertSender | None = None):  # fmt: skip
        self.source, self.settings, self.clock, self.log, self.alerts = source, settings, clock, log, alerts
        self.state, self.failures = State.CLOSED, 0
        self.cool_down = settings.cool_down_seconds
        self.opened_at: datetime | None = None
        self._restore()

    def _restore(self) -> None:
        """Picks up where an earlier process stopped. A closed or missing history is closed; anything else is open from
        the last row's time. A probe in flight when its process died leaves a half_open row: the breaker is open again
        from that time with the same cool-down (not doubled)."""
        last = self.log.last(self.source) if self.log else None
        if last is None or last.event == CLOSED:
            return
        self.state, self.opened_at, self.cool_down = State.OPEN, last.at, last.cool_down_seconds

    def check(self) -> Admission:
        """Asks leave to call. Raises Deferred (nothing sent) while open and cooling or while a probe is out."""
        if self.state is State.CLOSED:
            return Admission.CALL
        if self.state is State.HALF_OPEN:
            raise Deferred(self.source, "circuit half-open: a probe is already out")
        assert self.opened_at is not None
        reopens_at = self.opened_at + timedelta(seconds=self.cool_down)
        if self.clock() < reopens_at:
            raise Deferred(self.source, f"circuit open until {reopens_at.isoformat(timespec='seconds')}")
        self.state = State.HALF_OPEN
        self._log(HALF_OPEN)
        return Admission.PROBE

    def record_refusal(self) -> None:
        if self.state is State.HALF_OPEN:  # the probe failed: open again for twice as long
            self.cool_down = min(self.settings.cool_down_cap_seconds, self.cool_down * 2)
            self._open(REOPENED)
            return
        self.failures += 1
        if self.failures >= self.settings.threshold and self.state is State.CLOSED:
            self.cool_down = self.settings.cool_down_seconds
            self._open(OPENED)

    def record_other(self) -> None:
        """Any answer that is not a counted refusal: ends the run of consecutive refusals; a good probe closes it."""
        self.failures = 0
        if self.state is State.HALF_OPEN:
            self.state, self.cool_down, self.opened_at = State.CLOSED, self.settings.cool_down_seconds, None
            self._log(CLOSED)
            self._alert(ALERT_CLOSED.format(source=self.source))

    def _open(self, event: str) -> None:
        self.state, self.opened_at, self.failures = State.OPEN, self.clock(), 0
        self._log(event)
        self._alert(ALERT_OPENED.format(source=self.source, event=event, minutes=self.cool_down / 60))

    def _log(self, event: str) -> None:
        if self.log:
            self.log.append(Transition(self.clock(), self.source, event, self.cool_down))

    def _alert(self, text: str) -> None:
        if self.alerts:
            self.alerts.send(text)
