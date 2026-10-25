"""What the quality gate asks of the outside: the contracts NSE listed for a road's expiries (story 3.5). The leg
denominator is what was scheduled, so it comes from the listing and never from the capture it is judging."""

from collections.abc import Collection
from datetime import date
from typing import Protocol, runtime_checkable

from ..contracts.snapshot import ContractKey


class ListingUnavailable(Exception):
    """The archived listing file cannot be read or holds nothing for the expiries; the road cannot be judged."""


@runtime_checkable
class ListedContracts(Protocol):
    def contracts(
        self, underlying: str, expiries: Collection[date], session: date, spot: float
    ) -> frozenset[ContractKey]:
        """Every option contract NSE's previous-session F&O file lists for those expiries that the recorder takes at
        this spot (its 5% band). `ListingUnavailable` if the file cannot be read or lists none; a store outage is not
        that, it raises as itself."""
