"""The school's risk buckets (story 3.3 law 3, design 6.2): a new class behind C2's `BucketMap` interface, so C2's
`BucketCap` runs unedited. C2's own map knows NIFTY and BANKNIFTY only (`BUCKET_INDEX_GROUPS`); the pilot's roads add
FINNIFTY and MIDCPNIFTY. Groups (orchestrator, 22 Oct 2026, story section 6 item 8): {NIFTY}, {BANKNIFTY, FINNIFTY}
(FINNIFTY's largest weights are BANKNIFTY's banks: one shock hits both), {MIDCPNIFTY}. The sides come from the books
profile's `bucket_sides`, as C2's. A position on two indices, another index or an unlisted structure fails closed."""

from collections.abc import Iterable, Mapping

from ...contract_symbols import underlying_of
from ...risk.buckets import Bucket, BucketMap
from ...risk.inputs import RiskInputError

BANKS = "BANKNIFTY+FINNIFTY"
SCHOOL_GROUPS = {"NIFTY": "NIFTY", "BANKNIFTY": BANKS, "FINNIFTY": BANKS, "MIDCPNIFTY": "MIDCPNIFTY"}


class SchoolBuckets(BucketMap):
    def __init__(self, sides: Mapping[str, tuple[str, ...]]):
        self.sides = dict(sides)

    def buckets_of(self, structure: str, contracts: Iterable[str]) -> tuple[Bucket, ...]:
        groups = {underlying_of(c) for c in contracts}
        if len(groups) != 1 or not groups <= set(SCHOOL_GROUPS):
            raise RiskInputError(f"unmapped bucket: legs on {sorted(groups)}, not one of {sorted(SCHOOL_GROUPS)}")
        if structure not in self.sides:
            raise RiskInputError(f"unmapped bucket: structure {structure!r} has no side in the books' bucket_sides")
        group = SCHOOL_GROUPS[groups.pop()]
        return tuple(Bucket(group, side) for side in self.sides[structure])
