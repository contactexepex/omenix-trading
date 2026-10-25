"""Groww's part of a slot (story MS-P0b section 2): six near-month futures quotes, four stock chains and one quote per
near-money leg (the chain has no bid or ask, P0 probe 1). Reads only through A16's `ReadOnlyGroww`; every call goes
through the slot's `PacedCaller`. The client is signed in once, outside any retry: a failed sign-in stops Groww for
the day, so no second sign-in is ever made (judge 626's audit condition; self-review 1)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime

from ..providers.groww import _payload, parse_groww_chain, parse_groww_quote_book
from .answers import RawAnswer
from .caller import PacedCaller, SourceStopped
from .constants import CHAINS, FUTURES, GROWW_FUTURE_SYMBOL, OPTION_TYPES, RowKind
from .groww_timeout import BoundedCall
from .rows import captured, missing
from .slot_capture import LotLookup, SlotCapture, near_money, near_monthly, parsed

QUOTE_FIELDS = ("last_price", "bid_price", "offer_price", "depth")
SIGN_IN_FAILED = "sign-in failed: {name}"


def future_symbol(underlying: str, expiry: date) -> str:
    return GROWW_FUTURE_SYMBOL.format(underlying=underlying, expiry=expiry, month=f"{expiry:%b}".upper())


class GrowwAnswers:
    """Turns an SDK call into a `RawAnswer`: an error becomes its code, timeout and rate-limit flags and class name.
    Each call is bounded by the request timeout; a call that hangs past it stops Groww (never a second call in
    flight beside it)."""

    def __init__(self, rate_limited: Callable[[Exception], bool], bounded: BoundedCall | None = None):
        self.rate_limited, self.bounded = rate_limited, bounded or BoundedCall()

    def ask(self, request: Callable[[], object], shape: Callable[[object], bool]) -> RawAnswer:
        try:
            payload = _payload(self.bounded.run(request))
        except Exception as error:  # any SDK error is judged, never raised past the caller
            code = str(getattr(error, "code", "") or "")
            return RawAnswer(status=int(code) if code.isdigit() else None, rate_limited=self.rate_limited(error),
                             timed_out="Timeout" in type(error).__name__, error_name=type(error).__name__)  # fmt: skip
        return RawAnswer(payload=payload, shape_ok=shape(payload))


def _is_quote(payload: object) -> bool:
    return isinstance(payload, dict) and any(payload.get(field) for field in QUOTE_FIELDS)


def _has_strikes(payload: object) -> bool:
    return isinstance(payload, dict) and isinstance(payload.get("strikes"), dict) and bool(payload["strikes"])


def _has_expiries(payload: object) -> bool:
    return isinstance(payload, dict) and isinstance(payload.get("expiries"), list) and bool(payload["expiries"])


class GrowwReader:
    def __init__(self, client, answers: GrowwAnswers, lot: LotLookup, now: Callable[[], datetime]):
        self.client, self.answers, self.lot, self.now = client, answers, lot, now
        self.expiries: dict[str, date | None] = {}
        self._signed_in: tuple[str, str] | None = None

    def unlooked(self) -> list[str]:
        """The underlyings whose near-month expiry is not known yet (all of them before the first lookup)."""
        return [underlying for underlying in FUTURES if underlying not in self.expiries]

    def read_expiries(self, caller: PacedCaller, session: date) -> None:
        """Each underlying not looked up yet: its near-month expiry from this year's listing. A lookup that failed
        is tried again in the next slot, inside that slot's budget."""
        exchange, _ = self._sign_in()
        for underlying in self.unlooked():
            answer = caller.call("expiries", lambda u=underlying: self.answers.ask(
                lambda: self.client.get_expiries(exchange=exchange, underlying_symbol=u, year=session.year),
                _has_expiries))  # fmt: skip
            if answer is not None:
                listed = parsed(lambda a=answer: [date.fromisoformat(str(d)) for d in a.payload["expiries"]])
                self.expiries[underlying] = near_monthly(listed, session)

    def read_slot(self, caller: PacedCaller, capture: SlotCapture) -> None:
        self._sign_in()
        last = {underlying: self._future(caller, capture, underlying) for underlying in FUTURES}
        for underlying in CHAINS:
            self._chain(caller, capture, underlying, last.get(underlying))

    def _sign_in(self) -> tuple[str, str]:
        """The exchange and segment names, read once: the first read signs in. Whatever its failure, it is a stop for
        the day (never judged as a timeout or 5xx to retry), and a stopped source is never asked again that day."""
        if self._signed_in is None:
            try:
                self._signed_in = (self.client.EXCHANGE_NSE, self.client.SEGMENT_FNO)
            except Exception as error:
                raise SourceStopped(SIGN_IN_FAILED.format(name=type(error).__name__)) from None
        return self._signed_in

    def _quote(self, symbol: str) -> RawAnswer:
        exchange, segment = self._sign_in()
        return self.answers.ask(lambda: self.client.get_quote(trading_symbol=symbol, exchange=exchange,
                                                              segment=segment), _is_quote)  # fmt: skip

    def _future(self, caller: PacedCaller, capture: SlotCapture, underlying: str) -> float | None:
        expiry = self.expiries.get(underlying)
        if expiry is None:
            capture.rows.append(missing(RowKind.FUTURE, underlying, "", None, self.now()))
            return None
        return self._quoted(caller, capture, RowKind.FUTURE, underlying, future_symbol(underlying, expiry), expiry)

    def _quoted(self, caller, capture, kind, underlying: str, symbol: str, expiry: date) -> float | None:
        answer = caller.call(kind.value, lambda: self._quote(symbol))
        seen = self.now()
        if answer is None:
            capture.rows.append(missing(kind, underlying, symbol, expiry, seen))
            return None
        book = parsed(lambda: parse_groww_quote_book(symbol, answer.payload))
        digest = capture.keep(f"quote {symbol}", seen, answer)
        # Groww's quote has no time of its own (its last trade time is a trade's, not the quote's): source time none
        capture.rows.append(captured(kind, underlying, symbol, expiry, self.lot(underlying, expiry), book.bid,
                                     book.ask, None, seen, digest))  # fmt: skip
        return book.last

    def _chain(self, caller, capture: SlotCapture, underlying: str, future_last: float | None) -> None:
        expiry = self.expiries.get(underlying)
        if expiry is None:
            return
        exchange, _ = self._sign_in()
        answer = caller.call(
            "chain",
            lambda: self.answers.ask(
                lambda: self.client.get_option_chain(
                    exchange=exchange, underlying=underlying, expiry_date=expiry.isoformat()
                ),
                _has_strikes,
            ),
        )
        seen = self.now()
        if answer is None:
            capture.rows.append(missing(RowKind.OPTION, underlying, "chain", expiry, seen))
            return
        capture.keep(f"chain {underlying} {expiry}", seen, answer)
        chain = parsed(lambda: parse_groww_chain(answer.payload, underlying, expiry, 0, at=seen))
        for strike in near_money([s for s, _ in chain.quotes], future_last or chain.spot):
            for kind in OPTION_TYPES:
                leg = chain.get(strike, kind)
                if leg is not None and leg.symbol:
                    self._quoted(caller, capture, RowKind.OPTION, underlying, leg.symbol, expiry)
                else:
                    capture.rows.append(missing(RowKind.OPTION, underlying, f"{strike:g}{kind}", expiry, seen))
