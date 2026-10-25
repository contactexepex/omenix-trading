"""NSE's part of a slot (story MS-P0b section 2): one page visit, six near-month futures quotes and four stock chains
(NSE's chain carries bid and ask per strike). GET only, with the fixed honest User-Agent and never a browser's; every
request goes through the slot's `PacedCaller`."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime

import requests

from ..models import IST
from ..providers.public import parse_nse_chain, parse_nse_date
from .answers import RawAnswer
from .caller import PacedCaller
from .constants import (
    CHAINS,
    FUTURES,
    NSE_ACCEPT,
    NSE_CHAIN_PATH,
    NSE_FUTURES_PATH,
    NSE_HOST,
    NSE_PAGE,
    NSE_USER_AGENT,
    OPTION_TYPES,
    REQUEST_TIMEOUT_SECONDS,
    RowKind,
)
from .rows import captured, missing
from .slot_capture import LotLookup, SlotCapture, near_money, parsed

NSE_TIME = "%d-%b-%Y %H:%M:%S"
FUTURE_TYPES = ("Index Futures", "Stock Futures")


class NseGet:
    """The only way the probe reaches NSE: a GET with the honest headers, turned into a `RawAnswer`."""

    def __init__(self, session: requests.Session | None = None):
        self.session = session or requests.Session()
        self.session.headers.clear()
        self.session.headers.update({"User-Agent": NSE_USER_AGENT, "Accept": NSE_ACCEPT})

    def get(self, path: str, params: dict | None, shape: Callable[[object], bool]) -> RawAnswer:
        try:
            response = self.session.get(NSE_HOST + path, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
        except requests.Timeout:
            return RawAnswer(timed_out=True)
        except requests.RequestException as error:
            return RawAnswer(timed_out=isinstance(error, requests.ConnectionError), error_name=type(error).__name__)
        if response.status_code != 200:
            return RawAnswer(status=response.status_code)
        if shape is _is_page:
            return RawAnswer(status=200, payload={"page_bytes": len(response.content)}, shape_ok=bool(response.content))
        try:
            payload = response.json()
        except ValueError:
            return RawAnswer(status=200)
        return RawAnswer(status=200, payload=payload, shape_ok=shape(payload))


def _is_page(payload: object) -> bool:
    return True


def _has_stocks(payload: object) -> bool:
    return isinstance(payload, dict) and isinstance(payload.get("stocks"), list) and bool(payload["stocks"])


def _has_records(payload: object) -> bool:
    records = payload.get("records") if isinstance(payload, dict) else None
    return isinstance(records, dict) and isinstance(records.get("data"), list) and "underlyingValue" in records


def nse_time(text: object) -> datetime | None:
    try:
        return datetime.strptime(str(text), NSE_TIME).replace(tzinfo=IST)
    except ValueError:
        return None


def near_future(payload: dict, session: date) -> dict | None:
    """The near-month future's entry of a quote-derivative answer: futures only, the first expiry on or after today."""
    futures = []
    for entry in payload.get("stocks", []):
        meta = entry.get("metadata") or {}
        if meta.get("instrumentType") in FUTURE_TYPES:
            try:
                expiry = parse_nse_date(str(meta.get("expiryDate")))
            except ValueError:
                continue
            if expiry >= session:
                futures.append((expiry, entry))
    return min(futures, key=lambda pair: pair[0])[1] if futures else None


def _top(book: dict, side: str) -> float | None:
    levels = (book or {}).get(side) or [{}]
    price = levels[0].get("price")
    return float(price) if price else None


class NseReader:
    def __init__(self, http: NseGet, lot: LotLookup, now: Callable[[], datetime]):
        self.http, self.lot, self.now = http, lot, now

    def read_slot(self, caller: PacedCaller, capture: SlotCapture, session: date) -> None:
        caller.call("page", lambda: self.http.get(NSE_PAGE, None, _is_page))
        last = {underlying: self._future(caller, capture, underlying, session) for underlying in FUTURES}
        for underlying in CHAINS:
            self._chain(caller, capture, underlying, session, last.get(underlying))

    def _future(self, caller, capture: SlotCapture, underlying: str, session: date) -> float | None:
        answer = caller.call("future", lambda: self.http.get(NSE_FUTURES_PATH, {"symbol": underlying}, _has_stocks))
        seen = self.now()
        entry = parsed(lambda: near_future(answer.payload, session)) if answer else None
        if entry is None:
            capture.rows.append(missing(RowKind.FUTURE, underlying, "", None, seen))
            return None
        digest = capture.keep(f"future {underlying}", seen, answer)
        return parsed(lambda: self._future_row(capture, underlying, entry, answer.payload, seen, digest))

    def _future_row(self, capture, underlying: str, entry: dict, payload: dict, seen, digest: str) -> float | None:
        meta, book = entry.get("metadata") or {}, entry.get("marketDeptOrderBook") or {}
        expiry = parse_nse_date(str(meta["expiryDate"]))
        contract = str(meta.get("identifier") or f"{underlying} FUT {expiry}")
        source_time = nse_time(payload.get("fut_timestamp"))
        capture.rows.append(captured(RowKind.FUTURE, underlying, contract, expiry, self.lot(underlying, expiry),
                                     _top(book, "bid"), _top(book, "ask"), source_time, seen, digest))  # fmt: skip
        last = meta.get("lastPrice")
        return float(last) if last else None

    def _chain(self, caller, capture: SlotCapture, underlying: str, session: date, future_last: float | None) -> None:
        answer = caller.call("chain", lambda: self.http.get(NSE_CHAIN_PATH, {"symbol": underlying}, _has_records))
        seen = self.now()
        expiry = parsed(lambda: self._near_expiry(answer.payload, session)) if answer else None
        if expiry is None:
            capture.rows.append(missing(RowKind.OPTION, underlying, "chain", None, seen))
            return
        digest = capture.keep(f"chain {underlying}", seen, answer)
        chain = parsed(lambda: parse_nse_chain(answer.payload, underlying, expiry, 0))
        lot = self.lot(underlying, expiry)
        for strike in near_money([s for s, _ in chain.quotes], future_last or chain.spot):
            for kind in OPTION_TYPES:
                leg = chain.get(strike, kind)
                name = f"{underlying} {expiry} {strike:g} {kind}"
                if leg is None:
                    capture.rows.append(missing(RowKind.OPTION, underlying, name, expiry, seen))
                    continue
                capture.rows.append(captured(RowKind.OPTION, underlying, leg.symbol or name, expiry, lot, leg.bid,
                                             leg.ask, chain.timestamp, seen, digest))  # fmt: skip

    @staticmethod
    def _near_expiry(payload: dict, session: date) -> date | None:
        listed = []
        for text in (payload.get("records") or {}).get("expiryDates") or []:
            try:
                listed.append(parse_nse_date(str(text)))
            except ValueError:
                continue
        ahead = sorted(e for e in listed if e >= session)
        return ahead[0] if ahead else None
