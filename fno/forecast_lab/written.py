"""A written 15:45 report (story FL1-1, judge 422): its text, its alerts and what it covered, so the next report takes
up what this one could not. Coverage is kept per underlying and target day: `checked` (the seals of that day's
forecasts were checked and any missing or late one alerted) and `matched` (that day's forecasts were matched against
its official close). A target is checked on its own day (its seal deadlines have passed by 15:45) and matched once its
close is archived, which NSE does in the evening: so in the next report, or a later one if the archive is late.

The evening edition (FL1-1d) also keeps its verdicts: for each index, today's close as NSE's index list gave it and
whether it fell inside the forecast's ranges. The next morning confirms each against G13b's official close."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .delivery import Attachment


def key(underlying: str, day: date) -> str:
    return f"{underlying} {day.isoformat()}"


@dataclass(frozen=True)
class Verdict:
    """The evening's check of one index's forecast for today, on NSE's close before the official file."""

    underlying: str
    day: date
    method: str
    close: float
    inside_50: bool
    inside_90: bool
    band: tuple[float, float, float, float]  # the 5, 25, 75 and 95% levels it was checked against

    def inside(self, close: float) -> tuple[bool, bool]:
        """(inside "most likely", inside "almost certainly") for another close, against the same band."""
        q05, q25, q75, q95 = self.band
        return q25 <= close <= q75, q05 <= close <= q95


@dataclass(frozen=True)
class WrittenReport:
    text: str
    alerts: tuple[str, ...]
    checked: tuple[str, ...] = ()
    matched: tuple[str, ...] = ()
    attachments: tuple[Attachment, ...] = ()  # the picture and the details file (FL1-1c), posted with the text
    verdicts: tuple[Verdict, ...] = ()  # the evening edition's checks on NSE's close (FL1-1d)
