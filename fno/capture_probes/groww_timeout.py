"""A Groww call bounded by the probe's request timeout (story MS-P0b section 3; self-review 5): the SDK sets none we
can rely on, so each call runs on one worker thread and a call still running after the timeout counts as hung. A hung
call is never retried: a retry would put a second request in flight beside it, so it stops Groww for the run."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout

from .constants import REQUEST_TIMEOUT_SECONDS


class GrowwCallHung(Exception):
    """Raised when a call has not answered within the timeout; its class name is the stop reason."""


class BoundedCall:
    def __init__(self, timeout_seconds: float = REQUEST_TIMEOUT_SECONDS):
        self.timeout = timeout_seconds
        self._worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix="p0b-groww")
        self._hung = False

    def run(self, request: Callable[[], object]) -> object:
        if self._hung:
            raise GrowwCallHung()
        future = self._worker.submit(request)
        try:
            return future.result(timeout=self.timeout)
        except FutureTimeout:
            self._hung = True
            self._worker.shutdown(wait=False)
            raise GrowwCallHung() from None
