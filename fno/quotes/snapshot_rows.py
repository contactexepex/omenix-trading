"""One 3 pm snapshot row and the snapshot CSV (stories A4, A4f), apart from `recorder.py`, which reached the size limit.

`open_interest` (A4f, the last column) is the chain leg's open interest as of the chain call, seconds before the row's
own quote request; a leg the chain does not list gives an empty cell. Groww's chain parser turns a missing field into
0 (`fno/providers/groww.py`), so a reader treats 0 as unknown, never as "no open interest"."""

from __future__ import annotations

import csv
import io
from datetime import date

from ..models import OptionChain, QuoteBook
from .book_fetch import Fetched
from .quote_validity import quote_validity

COLUMNS = (
    "snapshot_id", "request_sent_at", "response_received_at", "quote_time", "age_basis", "freshness_proxy",
    "last_trade_time",
    "provider", "contract_id", "expiry", "strike", "type", "bid", "ask", "last", "bid_qty", "ask_qty", "spot",
    "book_source", "valid", "invalid_reason", "raw_sha256", "open_interest",
)  # fmt: skip
NO_QUOTE_TIME = "unknown: provider gives no quote timestamp"
PAGE_TIME = "provider's snapshot timestamp (NSE page time, one for the whole chain)"
FRESHNESS_PROXY = "same-day trade (market active; quote age unknown)"
VOLUME_PROXY = "day volume above zero (NSE gives no last trade time)"


def snapshot_row(snapshot_id: str, provider: str, got: Fetched, chain: OptionChain, day: date) -> dict:
    book: QuoteBook | None = got.book
    reason = quote_validity(book, day)
    leg = chain.get(got.strike, got.kind)
    return {
        "snapshot_id": snapshot_id, "request_sent_at": got.sent.isoformat(),
        "response_received_at": got.received.isoformat(),
        "quote_time": book.quote_time.isoformat() if book and book.quote_time else "",
        "age_basis": PAGE_TIME if book and book.quote_time else NO_QUOTE_TIME,
        "freshness_proxy": _freshness_proxy(book),
        "provider": provider,
        "last_trade_time": book.last_trade_time.isoformat() if book and book.last_trade_time else "",
        "contract_id": book.symbol if book else (leg.symbol if leg else ""), "expiry": chain.expiry.isoformat(),
        "strike": f"{got.strike:g}", "type": got.kind, "bid": _num(book and book.bid), "ask": _num(book and book.ask),
        "last": _num(book and book.last), "bid_qty": _num(book and book.bid_qty),
        "ask_qty": _num(book and book.ask_qty), "spot": f"{chain.spot:.2f}",
        "book_source": book.book_source if book else "", "valid": "false" if reason else "true",
        "invalid_reason": reason, "raw_sha256": book.raw_sha256 if book else "",
        "open_interest": _whole(leg.oi) if leg else "",
    }  # fmt: skip


def snapshot_csv(rows: list[dict]) -> bytes:
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue().encode()


def _freshness_proxy(book: QuoteBook | None) -> str:
    return VOLUME_PROXY if book and book.last_trade_time is None and book.traded_today else FRESHNESS_PROXY


def _num(value) -> str:
    return "" if value is None or value is False else f"{float(value):g}"


def _whole(count: float) -> str:
    """A contract count in full (never `:g`, which keeps 6 significant digits: 12,345,675 would be 1.23457e+07)."""
    return str(round(count))
