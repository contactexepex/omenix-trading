"""The history port (story MS-SIM-a): one underlying's archived option closes for one session."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from typing import Protocol, runtime_checkable

from ...constants import ExpiryKind, OptionKind


@dataclass(frozen=True)
class ChainRow:
    expiry: date
    strike: float
    kind: OptionKind
    close: float  # the day's last trade; not a quote
    volume: int  # contracts traded that day: zero means the leg did not trade
    open_interest: int
    monthly: bool  # an index future is listed on this expiry that day (EDGE1's monthly rule); otherwise a weekly


@dataclass(frozen=True)
class DayChain:
    session: date
    underlying: str
    index_close: float | None  # None when the archive has no index close for the day
    rows: tuple[ChainRow, ...]
    lots: Mapping[date, int] = field(
        default_factory=dict, hash=False
    )  # expiry -> NSE's own board lot, where the file states it
    source: str = ""  # the archive format the day came from (udiff or legacy)

    def expiries(self, kind: ExpiryKind) -> tuple[date, ...]:
        """The expiries of that kind, nearest first."""
        want_monthly = kind is ExpiryKind.MONTHLY
        return tuple(sorted({r.expiry for r in self.rows if r.monthly is want_monthly}))

    def rows_on(self, expiry: date) -> tuple[ChainRow, ...]:
        return tuple(r for r in self.rows if r.expiry == expiry)


@runtime_checkable
class HistoricalChain(Protocol):
    def day(self, underlying: str, session: date) -> DayChain | None:
        """That session's chain, or None when the archive has no usable file for it. Never reads another day."""
