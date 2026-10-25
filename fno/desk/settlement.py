"""NSE's final settlement of expired index options (story E7). NIFTY options are cash-settled: a leg still open at
expiry closes at its intrinsic value against the final settlement price of the index.

Where the price comes from: NSE's daily F&O file (UDiFF, A2) **of the expiry day only** (point in time). In that file,
every row of the expiring NIFTY contracts (the future and every option) carries the index's final settlement price in
`SttlmPric`; an option row's `SttlmPric` is not the option's value, and its `ClsPric` is not its settlement value
(checked on NSE's 25 Jan 2024 file: 21300 CE closed at 19.70, `SttlmPric` 21352.60, settlement value 52.60). The
price is used only when every expiring row agrees on it; anything else is refused, never guessed.
"""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime, time

from ..accounting.ledgers import Order
from ..books.fills import Fill
from ..constants import FILL_SETTLE, INDEX_FUTURE, INDEX_OPTION
from ..fo_bhavcopy import read_fo_file
from ..models import IST
from ..storage.raw_library import RawFileLibrary
from ..storage.raw_source import NseDailyFoSource
from .execution import fill_id
from .pricing import DeskLeg
from .records import FillRecord

SETTLEMENT_TIME = time(15, 30)  # the close of the expiry day's session, when the contract settles
SETTLEMENT_SNAPSHOT = "nse-final-settlement:{expiry}"  # what a settlement row names in place of a quote snapshot


class SettlementError(ValueError):
    """The expiry day's file is there but does not give one clear final settlement price."""


@dataclass(frozen=True)
class FinalSettlement:
    underlying: str
    expiry: date
    price: float  # the index's final settlement price
    source: str  # the file it was read from
    sha256: str  # of that file


class SettlementPrices(ABC):
    @abstractmethod
    def final_settlement(self, underlying: str, expiry: date) -> FinalSettlement | None:
        """The final settlement of that expiry; None while its file is not yet published (`SettlementError` when the
        file cannot give one clear price)."""


class NseFinalSettlement(SettlementPrices):
    def __init__(self, library: RawFileLibrary):
        self.library = library

    def final_settlement(self, underlying: str, expiry: date) -> FinalSettlement | None:
        path = NseDailyFoSource.path_for(expiry)
        found = self.library.get(path)
        if found.data is None:
            return None
        rows = [
            r for r in read_fo_file(NseDailyFoSource.filename_for(expiry), found.data)
            if r["TckrSymb"] == underlying and r["XpryDt"] == expiry.isoformat()
            and r["FinInstrmTp"] in (INDEX_FUTURE, INDEX_OPTION)
        ]  # fmt: skip
        what = f"{underlying} {expiry} in {path}"
        if not rows or any(r["TradDt"] != expiry.isoformat() for r in rows):
            raise SettlementError(f"no expiring contracts traded on the expiry day for {what}")
        prices = {float(r["SttlmPric"]) if r["SttlmPric"] else 0.0 for r in rows}
        if len(prices) != 1 or not min(prices) > 0:
            raise SettlementError(f"the expiring contracts disagree on the final settlement price for {what}: {prices}")
        return FinalSettlement(underlying, expiry, prices.pop(), path, hashlib.sha256(found.data).hexdigest())


def settlement_record(book: str, strategy: str, decision_id: str, trade_id: str, leg: DeskLeg, units: int,
                      final: FinalSettlement, charges: dict) -> FillRecord:  # fmt: skip
    """The leg closed at its intrinsic value against the final settlement price, with C1's settlement charges."""
    order = Order(leg.side(opening=False), leg.leg.intrinsic(final.price), units, 0.0, settlement=True)
    settled_at = datetime.combine(final.expiry, SETTLEMENT_TIME, IST)
    fill = Fill.priced(fill_id(trade_id, FILL_SETTLE, leg.contract), trade_id, settled_at, leg.contract, order, charges)
    snapshot = SETTLEMENT_SNAPSHOT.format(expiry=final.expiry.isoformat())
    return FillRecord(book, strategy, decision_id, FILL_SETTLE, snapshot, final.sha256, leg, "", False, fill)
