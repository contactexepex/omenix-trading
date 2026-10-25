"""The reasons' data (story FL1-1d-2): each Section reads one source and gives a `SectionView` in exactly one state,
holding `Cue`s the page prints and never computes. A value is shown only inside its Section's expected as-of rule
(the story's table, judge 438); outside it the Section says "not out yet" (evening) or "not available" (morning),
never an older value as current. `failed` is a read error: one alert, and it is listed under the system line.

A cue is `used` only when the forecast itself reads it (the option prices for the implied range, past closes for the
others); everything else is `context`, never a cause (no G13b method reads VIX or any global cue: judge 438)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date

AVAILABLE, NOT_OUT_YET, NOT_AVAILABLE, FAILED = "available", "not_out_yet", "not_available", "failed"
USED, CONTEXT = "used", "context"


@dataclass(frozen=True)
class Cue:
    name: str  # "S&P 500", "India VIX", "RBI policy"
    value: float | None = None
    change: float | None = None  # in `unit` (a percentage for a level: "%", points for a yield)
    unit: str = ""
    as_of: date | None = None
    role: str = CONTEXT
    text: str | None = None  # a flag's words ("NIFTY expiry today"), or the used input's
    size: float | None = None  # |change| over the cue's own 60-session spread: ranks the key points (not printed)


@dataclass(frozen=True)
class SectionView:
    name: str
    status: str
    as_of: date | None = None
    items: tuple[Cue, ...] = field(default=())
    why: str = ""  # the reason for a state other than available, in words


class Section(ABC):
    """One source of cues. `edition` is "morning" or "evening"; a read error raises, the page makes it `failed`."""

    name: str = ""

    @abstractmethod
    def read(self, day: date, edition: str) -> SectionView: ...


def missing(name: str, edition: str, why: str) -> SectionView:
    """Outside its as-of rule: "not out yet" in the evening, "not available" in the morning."""
    return SectionView(name, NOT_OUT_YET if edition == "evening" else NOT_AVAILABLE, why=why)
