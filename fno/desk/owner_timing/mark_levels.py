"""The levels C2 reads at a due mark (judge 203 condition 3): NIFTY's spot and the futures, taken from the same copy
as the option quotes, each only when valid there. A16's spot is its own index rule (`index_check`: requested on time,
the source's time fresh); its future counts only when A4's quote rule passes (two-sided, sizes, a trade that session)
and it was requested at or after the mark. An A4 stand-in capture gives the spot and futures its recorder wrote."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from ...intraday.document import SnapshotDocument
from ...intraday.groww_source import PARSE_ERRORS
from ...intraday.status import index_check
from ...providers.groww import parse_groww_quote_book
from ...quotes.recorder import quote_validity
from ...research_data.panel_reader import FutureQuote
from ..snapshot import ExecutionSnapshot

TRADED = 1  # a future valid by A4's rule traded that session: at least one contract, when Groww gives no volume


@dataclass(frozen=True)
class MarkSnapshot:
    """One due mark's copy: the option quotes E4 prices from, and the levels C2's fill-day check reads."""

    prices: ExecutionSnapshot
    spot: float | None  # None: not usable in this copy
    futures: tuple[FutureQuote, ...] = ()  # only the valid ones


def a16_spot(doc: SnapshotDocument) -> float | None:
    return index_check(doc).level


def a16_futures(doc: SnapshotDocument, day: date, mark: datetime) -> tuple[FutureQuote, ...]:
    call = doc.future
    if call is None or call.failure or not isinstance(call.payload, dict) or call.request_sent_at < mark:
        return ()
    try:
        book = parse_groww_quote_book(call.meta["symbol"], call.payload)
        expiry = date.fromisoformat(doc.expiries["monthly"])
    except (*PARSE_ERRORS, KeyError, TypeError):
        return ()  # an unreadable future is a missing one, never a guessed one
    if quote_validity(book, day) or not book.last:
        return ()
    volume = int(call.payload.get("volume") or TRADED)
    return (FutureQuote(expiry, book.last, 0.0, volume, 0),)
