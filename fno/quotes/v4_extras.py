"""What A4e's `v4` window records beside A4's two monthlies (story G10 completion, criterion 3a; G7b's asks): V4's
expiry (the first listed expiry with at least 5 scored sessions, chosen by G7b's `first_v4_expiry`, never copied) when
it is not one of the monthlies, at A4's 5% band, and one quote of the future of `e` (the nearest monthly strictly after
the day). Both go into the attempt's quote file only (Drive, A4b): the future as a `FUT` row. Neither decides whether
the attempt is complete: a failure is named in the sidecar and the pack carries what came (V4 or V5 then void
themselves). The sidecar names the chosen expiry as `v4_expiry`; a day the calendar cannot answer records `v4_expiry:
None` with `v4_expiry_note`, which the release alerts (judge 581 m2: the calendar ends on 31 Dec 2026)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime

from ..models import OptionChain, QuoteBook
from ..providers.base import Provider
from ..research_data.calendar import CalendarError
from .book_fetch import BookFetcher
from .capture_extras import CaptureExtras
from .future_quotes import FutureQuotes
from .quote_validity import quote_validity
from .snapshot_rows import COLUMNS, snapshot_row

FUTURE_KIND = "FUT"
RECORDED, NO_MONTHLY = "recorded", "no monthly after the day"  # `future_quote` when nothing failed
NOT_CHOSEN = "v4 expiry not chosen: {error}"
FAILED = "{what}: {kind} (provider message withheld)"


class V4Extras(CaptureExtras):
    def __init__(self, choose: Callable[[date, list[date]], date | None], provider: Provider, futures: FutureQuotes,
                 fetcher: Callable[[], BookFetcher], band: Callable[[OptionChain], list[tuple[float, str]]],
                 sent: Callable[[], datetime], now: Callable[[], datetime], underlying: str):  # fmt: skip
        """`choose(day, listed)`: G7b's rule; `fetcher()`: the window's book fetcher (no request after its end);
        `band(chain)`: A4's contracts within 5% of spot; `sent()`: a request's send time, raising after the window's
        end (A4e's `CaptureLog.request_allowed`)."""
        self.choose, self.provider, self.futures, self.fetcher, self.band = choose, provider, futures, fetcher, band
        self.sent, self.now, self.underlying, self._meta = sent, now, underlying, {}

    def capture(self, snapshot_id: str, day: date, listed: list[date], months: list[date]) -> list[dict]:
        self._meta = {"v4_expiry": None, "v4_failures": []}
        rows = self._v4_rows(snapshot_id, day, listed, months)
        return [*rows, *self._future_rows(snapshot_id, day, months)]

    def meta(self) -> dict:
        return self._meta

    def _v4_rows(self, snapshot_id: str, day: date, listed: list[date], months: list[date]) -> list[dict]:
        try:
            expiry = self.choose(day, listed)
        except CalendarError as error:
            self._meta["v4_expiry_note"] = NOT_CHOSEN.format(error=error)
            return []
        self._meta["v4_expiry"] = expiry.isoformat() if expiry else None
        if expiry is None or expiry in months:
            return []  # none listed with 5 sessions, or a monthly A4 records anyway
        try:
            chain = self.provider.chain(self.underlying, expiry)
        except Exception as error:  # named, never hidden; the monthlies' attempt is not made incomplete by it
            self._meta["v4_failures"].append(FAILED.format(what=f"chain {expiry}", kind=type(error).__name__))
            return []
        rows = []
        for got in self.fetcher().fetch(chain, self.band(chain)):
            if got.error is not None:
                self._meta["v4_failures"].append(FAILED.format(what=f"{expiry} {got.strike:g} {got.kind}",
                                                               kind=type(got.error).__name__))  # fmt: skip
                continue
            rows.append(snapshot_row(snapshot_id, self.provider.name, got, chain, day))
        return rows

    def _future_rows(self, snapshot_id: str, day: date, months: list[date]) -> list[dict]:
        expiry = min((m for m in months if m > day), default=None)
        if expiry is None:
            self._meta["future_quote"] = NO_MONTHLY
            return []
        try:
            sent = self.sent()
            book = self.futures.quote(expiry)
        except Exception as error:
            self._meta["future_quote"] = FAILED.format(what=f"future {expiry}", kind=type(error).__name__)
            return []
        self._meta["future_quote"] = RECORDED
        return [future_row(snapshot_id, self.provider.name, expiry, book, sent, self.now(), day)]


def future_row(snapshot_id: str, provider: str, expiry: date, book: QuoteBook, sent: datetime, received: datetime,
               day: date) -> dict:  # fmt: skip
    """The future's quote in A4's row form (its own `FUT` kind, no strike), so one quote file holds the attempt."""
    reason = quote_validity(book, day)
    row = dict.fromkeys(COLUMNS, "")
    row.update(snapshot_id=snapshot_id, request_sent_at=sent.isoformat(), response_received_at=received.isoformat(),
               last_trade_time=book.last_trade_time.isoformat() if book.last_trade_time else "", provider=provider,
               contract_id=book.symbol, expiry=expiry.isoformat(), type=FUTURE_KIND, bid=_num(book.bid),
               ask=_num(book.ask), last=_num(book.last), book_source=book.book_source,
               valid="false" if reason else "true", invalid_reason=reason, raw_sha256=book.raw_sha256)  # fmt: skip
    return row


def _num(value: float | None) -> str:
    return "" if value is None else f"{float(value):g}"
