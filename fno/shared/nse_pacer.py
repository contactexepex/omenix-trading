"""The pacer every NSE request goes through (story R1b): per host, one request a second, a pause after two refusals in a
row, and one probe when the pause ends. It is `RequestPacer` of story A9b rebuilt on the shared resilience layer
(`fno/shared/resilience/`): a `RateLimit` and a `CircuitBreaker` for each host, never one shared by both.

After the pause the first request goes alone (the probe). The others wait for its answer, at most `probe_wait_seconds`,
then go ahead if it closed the host, or are told the host is cooling off if it re-opened it. A 403 or 429 answer counts
as a refusal; any other answer, a 5xx included, closes it; a request that got no answer closes it too, as the old pacer
(which never saw a transport failure) left the door open after the pause."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import requests

from fno.shared.resilience.breaker import CircuitBreaker, State
from fno.shared.resilience.outcomes import Deferred
from fno.shared.resilience.rate_limit import RateLimit, RateSettings
from fno.shared.resilience.settings import settings_for

HOST_SPACING_SECONDS = {"www.nseindia.com": 1.0, "nsearchives.nseindia.com": 1.0}
DEFAULT_SPACING_SECONDS = 1.0
REFUSAL_STATUS_CODES = (403, 429)
PROBE_WAIT_SECONDS = 60.0  # the longest request timeout (a file); a waiter gives up on the probe after this
COOLING_OFF_MESSAGE = "{host} refused requests (HTTP {status}); not calling it for {minutes} minutes"
EPOCH = datetime(2000, 1, 1, tzinfo=UTC)
NO_WAIT_LIMIT = 24 * 3600.0  # spacing is never a deferral: the old pacer slept as long as it took


class SourceCoolingOff(requests.RequestException):
    """The host refused us recently; no request is sent until the cool-off ends."""


@dataclass
class _Host:
    rate: RateLimit
    breaker: CircuitBreaker
    answered: threading.Condition = field(default_factory=threading.Condition)
    last_refusal: int = 0  # the status of the refusal that opened the host; the message is built when it is raised


class NsePacer:
    def __init__(
        self,
        spacing: dict[str, float] | None = None,
        clock: Callable[[], float] | None = None,
        sleep: Callable[[float], None] = time.sleep,
        probe_wait_seconds: float = PROBE_WAIT_SECONDS,
    ):
        self.spacing = HOST_SPACING_SECONDS if spacing is None else spacing
        self.clock, self.sleep, self.probe_wait_seconds = clock or time.monotonic, sleep, probe_wait_seconds
        self._hosts: dict[str, _Host] = {}
        self._lock = threading.Lock()

    def wait_turn(self, host: str) -> None:
        """Block until the host may be called again; raise SourceCoolingOff if it is cooling off after a refusal. The
        request that follows an expired pause is the probe, and it goes alone: the rest wait for its answer."""
        state = self._host(host)
        while True:
            self._wait_for_probe(state)
            try:
                state.breaker.check()
            except Deferred:
                if state.breaker.state is State.HALF_OPEN:  # another thread has just become the probe: wait for it
                    continue
                raise SourceCoolingOff(self._message(host, state)) from None
            break
        state.rate.acquire()

    def observe(self, host: str, status: int) -> None:
        """The answer to a request: a refusal counts, anything else resets the run and ends a probe."""
        state = self._host(host)
        if status in REFUSAL_STATUS_CODES:
            state.last_refusal = status  # before the breaker can open: another thread may be refused at once
            state.breaker.record_refusal()
        else:
            state.breaker.record_other()
        self._release(state)

    def unanswered(self, host: str) -> None:
        """A request that got no answer or raised: the old pacer never heard of it, so it counts for nothing; it only
        ends a probe, which closes the host."""
        state = self._host(host)
        if state.breaker.state is State.HALF_OPEN:
            state.breaker.record_other()
        self._release(state)

    def _wait_for_probe(self, state: _Host) -> None:
        with state.answered:
            state.answered.wait_for(lambda: state.breaker.state is not State.HALF_OPEN, self.probe_wait_seconds)
            if state.breaker.state is State.HALF_OPEN:  # the probe never answered in time: treat it as unanswered
                state.breaker.record_other()

    @staticmethod
    def _message(host: str, state: _Host) -> str:
        minutes = round(state.breaker.cool_down / 60)
        return COOLING_OFF_MESSAGE.format(host=host, status=state.last_refusal, minutes=minutes)

    @staticmethod
    def _release(state: _Host) -> None:
        with state.answered:
            state.answered.notify_all()

    def _host(self, host: str) -> _Host:
        with self._lock:
            if host not in self._hosts:
                settings = settings_for("nse")
                breaker = CircuitBreaker(f"nse:{host}", settings.breaker, self._wall_clock)
                spacing = RateSettings(self.spacing.get(host, DEFAULT_SPACING_SECONDS), max_wait_seconds=NO_WAIT_LIMIT)
                self._hosts[host] = _Host(RateLimit(f"nse:{host}", spacing, None, self.sleep, self.clock), breaker)
            return self._hosts[host]

    def _wall_clock(self) -> datetime:
        return EPOCH + timedelta(seconds=self.clock())
