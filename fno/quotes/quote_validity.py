"""Story A4's rule for when a recorded quote is a usable two-sided market (moved out of `recorder.py` by story A4c to
keep that file under the size limit; unchanged)."""

from __future__ import annotations

from datetime import date

from ..models import QuoteBook


def traded_today(book: QuoteBook | None, today: date) -> bool:
    """A trade in the contract today: its last trade time (Groww) or, when the provider gives none, its day volume
    (NSE). Either proves the market was active in it today; neither proves the quote is seconds old."""
    if book is None:
        return False
    if book.last_trade_time is not None:
        return book.last_trade_time.date() == today
    return bool(book.traded_today)


def quote_validity(book: QuoteBook | None, today: date) -> str:
    """Empty when the quote is usable as a two-sided market; otherwise the reason it is not. Groww gives no quote
    timestamp, so the only freshness evidence is a trade in the contract today: without one the book is not valid.
    Even when valid, the quote's age is unknown (not proven to be seconds old)."""
    if book is None:
        return "no quote"
    if not book.bid or not book.ask:
        return "one-sided or empty book"
    if book.bid > book.ask:
        return "crossed (bid above ask)"
    if not book.bid_qty or not book.ask_qty:
        return "no size"
    if not traded_today(book, today):
        return "no trade today (quote age unknown, possibly stale)"
    if book.quote_time is not None and book.quote_time.date() != today:
        return "quote not from today"
    return ""
