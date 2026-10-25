"""`IndexSettlementSource` over NSE's already-archived F&O bhavcopy (story 3.6; owner decision 9a5f4d74: no new NSE
read). E7's `NseFinalSettlement` reads the expiry day's UDiFF file and needs every expiring row of the index to agree
on `SttlmPric`; it already works per underlying, so the school reuses it unchanged for all four indices. The library
it is given reads the stores only: `ArchivedOnly` is a source that never fetches, so a file not yet archived is
"not published yet" and the position stays `settlement_needed`."""

from datetime import date

from ...desk.settlement import SettlementError, SettlementPrices
from ...storage.raw_source import NseDailyFoSource, RawFileSource
from ..contracts.accounts import SettlementPrice, SettlementUnavailable
from ..contracts.roads import ROADS

SCHOOL_UNDERLYINGS = frozenset(road.underlying for road in ROADS)


class ArchivedOnly(RawFileSource):
    """Answers every request with "not published": the school never reads NSE itself."""

    name = "archived only"
    dataset = NseDailyFoSource.dataset

    def fetch(self, path: str) -> bytes | None:
        return None


class BhavcopySettlement:
    def __init__(self, prices: SettlementPrices):
        self.prices = prices

    def price(self, underlying: str, expiry: date) -> SettlementPrice:
        if underlying not in SCHOOL_UNDERLYINGS:
            raise ValueError(f"{underlying} is not a school road's index")
        try:
            final = self.prices.final_settlement(underlying, expiry)
        except SettlementError as unclear:
            raise SettlementUnavailable(str(unclear)) from unclear
        if final is None:
            raise SettlementUnavailable(f"{underlying} {expiry}: the expiry day's F&O file is not archived yet")
        return SettlementPrice(final.price, final.sha256)
