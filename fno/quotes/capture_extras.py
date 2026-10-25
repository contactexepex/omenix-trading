"""What a named capture records beside A4's own contracts (story G10 completion): an interface the recorder calls once
per attempt, apart from `recorder.py` (at its size limit) and free of provider imports, so the recorder stays A4's."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date


class CaptureExtras(ABC):
    @abstractmethod
    def capture(self, snapshot_id: str, day: date, listed: list[date], months: list[date]) -> list[dict]:
        """The extra quote rows of one attempt (never counted for its completeness); never raises for a failed
        request, which `meta()` names."""

    @abstractmethod
    def meta(self) -> dict:
        """The attempt's sidecar keys (no quote value: the sidecar is committed)."""
