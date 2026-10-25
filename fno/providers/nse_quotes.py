"""NSE's public option chain as a quote book for the 3 pm recorder (story O6, owner's choice (a) of 13 Oct 2026: no
broker key in GitHub). One chain request per expiry carries every contract's best bid and ask with their sizes, the
day's traded volume, and one page timestamp. NSE gives no per-contract last trade time, so "traded today" is proven by
day volume above zero, and the quote's age comes from the page timestamp, which Groww does not give at all."""

from __future__ import annotations

import hashlib
import json
from datetime import date

from ..models import OptionChain, QuoteBook
from .public import NSEProvider, parse_nse_chain

NSE_BOOK_SOURCE = "nse option chain (best bid/ask)"


def _number(value) -> float | None:
    """NSE writes 0 for an empty side of the book: that is no quote, not a price of zero."""
    return float(value) if value else None


class NseQuoteProvider(NSEProvider):
    """NSEProvider that also answers `quote_book` from the legs of the chain it last fetched for that expiry."""

    def __init__(self, config: dict, client=None):
        super().__init__(config, client)
        self._legs: dict[tuple[date, float, str], dict] = {}

    def chain(self, underlying: str, expiry: date) -> OptionChain:
        payload = self.chain_payload(underlying, expiry)
        chain = parse_nse_chain(payload, underlying, expiry, self.fallback_lot_size(underlying))
        for row in payload["records"].get("data", []):
            for kind in ("CE", "PE"):
                if row.get(kind):
                    self._legs[(expiry, float(row["strikePrice"]), kind)] = row[kind]
        return chain

    def quote_book(self, chain: OptionChain, strike: float, kind: str) -> QuoteBook | None:
        leg = self._legs.get((chain.expiry, strike, kind))
        if leg is None:
            return None
        raw = json.dumps({"timestamp": chain.timestamp.isoformat(), "leg": leg}, sort_keys=True).encode()
        return QuoteBook(
            symbol=leg.get("identifier") or "",
            bid=_number(leg.get("buyPrice1")),
            ask=_number(leg.get("sellPrice1")),
            bid_qty=_number(leg.get("buyQuantity1")),
            ask_qty=_number(leg.get("sellQuantity1")),
            last=_number(leg.get("lastPrice")),
            last_trade_time=None,
            book_source=NSE_BOOK_SOURCE,
            raw_sha256=hashlib.sha256(raw).hexdigest(),
            quote_time=chain.timestamp,
            traded_today=bool(leg.get("totalTradedVolume")),
        )
