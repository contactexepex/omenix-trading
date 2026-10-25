"""What the road catalogue asks of the outside: the dated lot and the listed expiries of a road (story 3, `roads/`)."""

from dataclasses import dataclass
from datetime import date
from typing import Protocol, runtime_checkable

from ..constants import ClosureReason
from ..contracts.roads import DatedLot, Road
from ..quality.ports import ListingUnavailable


class ExpiryUnavailable(ListingUnavailable):
    """The listing that says which expiries a road records cannot be read for the session."""


@dataclass(frozen=True)
class LotProblem:
    """Why a road has no lot that session: `LOT_UNAVAILABLE` (nothing usable to read) or `LOT_MISMATCH` (the expiries
    carry different lots), so a closure says what is true."""

    reason: ClosureReason


@runtime_checkable
class LotSource(Protocol):
    def lot(self, underlying: str, session: date, expiries: tuple[date, ...]) -> DatedLot | LotProblem:
        """The one lot in force that session for every expiry given, or the problem. `LOT_UNAVAILABLE`: no file for
        that session, an unreadable file, no row for the underlying or for an expiry month, or a lot of zero or less.
        `LOT_MISMATCH`: every expiry has a lot, but not the same one."""


@runtime_checkable
class ExpirySource(Protocol):
    def expected(self, road: Road, session: date) -> tuple[date, ...]:
        """The expiries the road's capture must record that session, nearest first (A4's two monthlies, A4f's two
        weeklies), worked out from NSE's stored F&O files, never from the capture itself."""
