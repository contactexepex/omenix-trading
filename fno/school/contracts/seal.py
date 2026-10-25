"""A dashcam seal (story 3.4): the file's SHA-256 and the commit that pushed its receipt, before any fill."""

from dataclasses import dataclass
from datetime import datetime


class StaleSeal(Exception):
    """A seal not pushed, pushed after the fill time, or naming another file's SHA-256."""


@dataclass(frozen=True)
class Seal:
    path: str  # the record file's Drive path
    sha256: str
    # The receipt commit's time. The proof that it was pushed is the receipt on the remote: `DashcamStore.seal`
    # returns a Seal only after that push succeeded, so a Seal in hand means pushed, committed at `pushed_at`.
    pushed_at: datetime
    commit: str  # the receipt's commit

    def __post_init__(self):
        if self.pushed_at.tzinfo is None or not self.sha256 or not self.commit:
            raise ValueError("a seal needs an aware push time, a SHA-256 and a commit")

    def covers(self, sha256: str, fill_time: datetime) -> bool:
        """True when this seal is for that file and was pushed no later than the fill."""
        return self.sha256 == sha256 and self.pushed_at <= fill_time
