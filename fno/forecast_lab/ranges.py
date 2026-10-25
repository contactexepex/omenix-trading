"""What FL1 reads from G13b (agreed with the G13 builder, 21 Oct 2026): a port FL1 owns as the consumer; G13b keeps its
own concrete reader (`fno/price_ranges/reader.py`) and FL1 owns the one adapter between them, so FL1 never builds a
Drive path and neither side waits for the other's branch. Each issue's rows, its seal time (the GitHub push time of its
receipt, never a commit date or the self-reported issue time), G13b's own scores and the official closes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime

STATUS_OK = "ok"


@dataclass(frozen=True)
class RangeRow:
    """One forecaster's range for one horizon: index levels at the 5-95% quantiles and P(close above s_ref)."""

    forecaster: str
    horizon: str  # "N0", "N1" or "N3"
    target_day: date
    quantiles: dict[float, float]
    p_up: float | None
    status: str
    reason: str = ""


@dataclass(frozen=True)
class SealedIssue:
    """One issue of one underlying on one day. `sealed_at` is None when no push evidence exists; `late` is G13b's own
    verdict against the issue's deadline. Either makes the issue late."""

    underlying: str
    day: date
    issue: str
    s_ref: float
    sealed_at: datetime | None
    rows: tuple[RangeRow, ...]
    late: bool = False

    def row(self, forecaster: str, horizon: str) -> RangeRow | None:
        return next((r for r in self.rows if (r.forecaster, r.horizon) == (forecaster, horizon)), None)


@dataclass(frozen=True)
class RangeScore:
    """G13b's score of one row against its target day's official close (FL1 never recomputes it). A coverage is None
    where it means nothing (a point-mass baseline)."""

    forecaster: str
    horizon: str
    issue: str
    issue_day: date
    target_day: date
    outcome: float
    quantile_score: float
    inside_25_75: bool | None
    inside_05_95: bool | None
    brier_up: float | None
    method: str = ""  # G13b's method SHA-256: scores of two method versions are never pooled


class RangeSource(ABC):
    @abstractmethod
    def sealed(self, underlying: str, day: date, issue: str) -> SealedIssue | None:
        """The issue as sealed, or None when it was never written."""

    @abstractmethod
    def scores(self, underlying: str, target_day: date) -> list[RangeScore]:
        """Every score whose target is `target_day`."""

    @abstractmethod
    def scored_days(self, underlying: str, through: date) -> list[date]:
        """The target days with at least one live score, up to `through` (the trust line's count)."""

    @abstractmethod
    def history(self, underlying: str, through: date) -> list[RangeScore]:
        """Every live score up to `through` (the running scoreboard); a forecast sealed late is never live."""


class Outcomes(ABC):
    @abstractmethod
    def close(self, underlying: str, day: date) -> float | None:
        """NSE's official index close of the day (the one G13b scores against), or None before it is archived."""


class TodayCloses(ABC):
    """The evening's own close of the day, read before NSE's official file (story FL1-1d; A4h's reader plugs in here).
    The value is labelled as such on the page, and the next morning confirms it against `Outcomes`."""

    @abstractmethod
    def close(self, underlying: str, day: date) -> float | None:
        """The day's close as read, or None when it was not read."""

    @abstractmethod
    def why_missing(self, day: date) -> str:
        """Why no close was read: the page says it in words."""

    def levels(self, underlying: str, day: date) -> dict[str, float]:
        """The day's other levels read with the close ("open", "high", "low"), each only when recorded (FL1-1f)."""
        return {}


class NoTodayCloses(TodayCloses):
    """Until A4h's reader exists: the evening says plainly that no close was read, and checks nothing."""

    REASON = "A4h's close reader is not built yet"

    def close(self, underlying: str, day: date) -> float | None:
        return None

    def why_missing(self, day: date) -> str:
        return self.REASON
