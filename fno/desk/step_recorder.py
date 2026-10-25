"""How the daily run records a finished step in its log (story O1-status-only). The desk's own default records the
result as given; the daily run's composition root (`fno/daily/wiring.py`) gives the recorder that keeps the committed
log to status only and the full text in a private log."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from .run_log import RunLog


class StepRecorder(ABC):
    @abstractmethod
    def record(self, log: RunLog, name: str, started: datetime, finished: datetime, inputs: dict, result: dict) -> None:
        """Records the step in `log`, which the run then commits."""


class AsGiven(StepRecorder):
    def record(self, log: RunLog, name: str, started: datetime, finished: datetime, inputs: dict, result: dict) -> None:
        log.record(name, started, finished, inputs, result)
