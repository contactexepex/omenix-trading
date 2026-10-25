"""The flat 09:15 labels read beside the capture (story A22d): started when the run starts and taken when the day row
is written, so no Drive wait in it can move GIFT Nifty's 08:40 read or the 09:12 commit (judge 589 finding 1). Not
read by then, or read with an error: every flat value is `unverified`, with one problem line."""

from __future__ import annotations

import threading
from collections.abc import Callable

from .problems import Problem

STEP = "open check labels"
NOT_IN_TIME = "not read by the day row; flat values labelled unverified"
FINISH_WITHIN_SECONDS = 600  # after the capture's commits nothing waits on it; bounded so the routine always ends


class LabelRead:
    def __init__(self, read: Callable[[], dict[str, str]]):
        self._labels: dict[str, str] | None = None
        self._error: BaseException | None = None
        self._thread = threading.Thread(target=self._read, args=(read,), daemon=True)  # never holds the run's exit
        self._thread.start()

    def _read(self, read: Callable[[], dict[str, str]]) -> None:
        try:
            self._labels = read()
        except Exception as error:  # a thread's error is lost unless kept: it becomes the run's problem line
            self._error = error

    def finish(self) -> None:
        """Waits (bounded) for a late read before the open check uses the same Drive cache, so the two never write the
        same cached file at once."""
        self._thread.join(FINISH_WITHIN_SECONDS)

    def taken(self) -> tuple[dict[str, str], list[Problem]]:
        """The labels now, without waiting: empty (all `unverified`) with its problem while not ready or failed."""
        if self._thread.is_alive():
            return {}, [Problem(STEP, "late", NOT_IN_TIME)]
        if self._error is not None:
            return {}, [Problem(STEP, "failed", type(self._error).__name__)]
        return self._labels or {}, []
