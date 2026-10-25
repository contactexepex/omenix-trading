"""Risk buckets (story C5, design 6.2): positions sharing an underlying group and a side of exposure.

One crash or one squeeze hits a whole bucket, so its cap counts the bucket's positions together. A position is in one
bucket per side its structure has: a fly or condor in one volatility side; a directional spread both in its direction
and in a volatility side (owner, 15 Oct 2026, "1 B": a crash hits both), with its full maximum loss in each. Its
underlying group is read from its contracts' exchange symbols in either provider's format (`fno/contract_symbols.py`:
Groww's `NIFTY26OCT25000CE` and NSE's `OPTIDXNIFTY13-10-2026CE21950.00` are both NIFTY), its side from its structure
code through the profile's `bucket_sides`. Fail closed (design 6.1a): a position that cannot be mapped (a structure code
not listed, legs on two underlyings, a stock or an index 6.2 does not name) is an input error, so the trade is refused.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from ..constants import BUCKET_INDEX_GROUPS
from ..contract_symbols import underlying_of
from .inputs import RiskInputError


@dataclass(frozen=True)
class Bucket:
    group: str  # NIFTY, BANKNIFTY (stocks and "stock results this week" are not mapped yet)
    side: str  # one of BUCKET_SIDES

    def __str__(self) -> str:
        return f"{self.group}/{self.side}"


class BucketMap(ABC):
    """Which bucket a position belongs to."""

    @abstractmethod
    def buckets_of(self, structure: str, contracts: Iterable[str]) -> tuple[Bucket, ...]:
        """The position's buckets; RiskInputError when it cannot be mapped."""


class StructureBuckets(BucketMap):
    """Group from the contracts, side from the structure code (`risk.profiles.<profile>.bucket_sides`)."""

    def __init__(self, sides: Mapping[str, tuple[str, ...]]):
        self.sides = dict(sides)

    def buckets_of(self, structure: str, contracts: Iterable[str]) -> tuple[Bucket, ...]:
        groups = {underlying_of(c) for c in contracts}
        if len(groups) != 1:
            raise RiskInputError(f"unmapped bucket: the legs are on {sorted(groups) or 'no'} underlyings, not one")
        group = groups.pop()
        if group not in BUCKET_INDEX_GROUPS:
            raise RiskInputError(f"unmapped bucket: underlying {group!r} is not one of {BUCKET_INDEX_GROUPS}")
        if structure not in self.sides:
            raise RiskInputError(
                f"unmapped bucket: structure {structure!r} has no side in risk.profiles.<profile>.bucket_sides"
            )
        return tuple(Bucket(group, side) for side in self.sides[structure])
