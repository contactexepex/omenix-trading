"""When GitHub received a family's commitment (story G10 part 2, section 5): a live v4 record counts only if the
commit that added it reached GitHub by 15:10:00 IST. The time is GitHub's receipt time, never the commit's own date.
Behind an interface; the one adapter reads O8's evidence (F1's GitHub push receipts)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, datetime

from ..forecast_v4.terms import V4_DEADLINE
from ..health.evidence import Evidence
from ..health.model import EvidenceUnknown
from ..models import IST


class CommitmentTimeUnknown(RuntimeError):
    """GitHub's receipt time cannot be found: no verdict is written (never a guessed time)."""


class CommitmentTimes(ABC):
    @abstractmethod
    def file_received_at(self, path: str) -> datetime:
        """GitHub's receipt time of the commit that first added the repository file `path`."""

    @abstractmethod
    def row_received_at(self, path: str, row_text: str, day: date) -> datetime:
        """GitHub's receipt time of the commit that added `row_text` to `path` (a v4 record is one CSV row)."""


def on_time(received: datetime, day: date) -> bool:
    """Received by 15:10:00 IST on the day: 15:10:00 counts, 15:10:01 is a miss."""
    return received <= datetime.combine(day, V4_DEADLINE, IST)


class GitHubCommitmentTimes(CommitmentTimes):
    def __init__(self, evidence: Evidence):
        self.evidence = evidence

    def file_received_at(self, path: str) -> datetime:
        return self._known(lambda: self.evidence.file_pushed_at(path))

    def row_received_at(self, path: str, row_text: str, day: date) -> datetime:
        return self._known(lambda: self.evidence.row_pushed_at(path, row_text, day))

    @staticmethod
    def _known(read) -> datetime:
        try:
            received = read()
        except EvidenceUnknown as unknown:
            raise CommitmentTimeUnknown(str(unknown)) from None
        if received.tzinfo is None:
            raise CommitmentTimeUnknown("GitHub's receipt time has no offset")
        return received
