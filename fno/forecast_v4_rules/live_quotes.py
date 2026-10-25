"""A live two-sided quote in the v4 pack (PROTOCOL_v4.md sections 1.4 and 1.5, wording W5; story G7b completion): a bid
above 0 and an ask not below it, both present, a trade in the contract on the day (A4's own `traded_today` rule, called
through a small adapter, never copied: Groww gives no quote time, so a trade today is the only freshness evidence), and
a spread of at most 5% of the mid. Sizes are not checked: the pack carries none and the protocol asks for none."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from ..models import QuoteBook
from ..quotes.quote_validity import traded_today

SPREAD_LIMIT = Decimal("0.05")  # (ask - bid) / mid; exactly 5% passes, in exact decimals (7.02 / 7.38 is 5%)
NO_QUOTE, NO_TRADE_TODAY, SPREAD = "no_quote", "no_trade_today", "spread"


@dataclass(frozen=True)
class TwoSided:
    bid: float | None
    ask: float | None
    last_trade_time: datetime | None  # the contract's last trade (Groww)
    traded_flag: bool | None = None  # the day's volume > 0, where the source gives no last trade time

    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2


def quote_problem(quote: TwoSided, day: date) -> str:
    """Empty when the quote is live and two-sided under the 5% rule; otherwise why not."""
    if quote.bid is None or quote.ask is None or quote.bid <= 0 or quote.ask < quote.bid:
        return NO_QUOTE
    book = QuoteBook("", quote.bid, quote.ask, None, None, None, quote.last_trade_time, "", "",
                     traded_today=quote.traded_flag)  # fmt: skip
    if not traded_today(book, day):
        return NO_TRADE_TODAY
    bid, ask = Decimal(repr(quote.bid)), Decimal(repr(quote.ask))
    return SPREAD if (ask - bid) * 2 > SPREAD_LIMIT * (ask + bid) else ""
