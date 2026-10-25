"""What one recorder captures and how (story A4c). NIFTY's slot is A4's, unchanged; the other traded indices record
after NIFTY's push, paced, inside their own window, and a quiet index is never read as a closed market."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time

from ..constants import NIFTY_SYMBOL


@dataclass(frozen=True)
class Slot:
    underlying: str = NIFTY_SYMBOL
    cross_check: bool = True  # "calendar says session, no same-day trades": NIFTY's check only (response 144 finding 3)
    stop_requests_at: time | None = None  # no request starts after it (response 144 finding 5)
    workers: int = 1
    per_second: float | None = None  # request starts a second, shared Groww key (A16's measured limit)
    check_listed: bool = False  # the previous session's NSE file must list the underlying as an index option
    weeklies: int = 0  # A4f: record this many nearest weekly expiries instead of the two monthlies
    stem_suffix: str = ""  # A4f: `weekly` gives the stem `niftyweekly`

    @property
    def stem(self) -> str:
        """File-name prefix: `nifty` for NIFTY, so A4's names stay byte for byte."""
        return self.underlying.lower() + self.stem_suffix


NIFTY_SLOT = Slot()
