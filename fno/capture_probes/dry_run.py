"""The probe's dry run (story MS-P0b criterion 13): the committed code over made-up answers, on a clock that jumps
instead of waiting. Every price here is invented; nothing reaches Groww, NSE, Drive, Slack or git."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

from ..models import IST
from .constants import FUTURES, SLOTS

CALL_SECONDS = 0.2  # each made-up answer "takes" this long, so latency figures are not all zero
MADE_UP_LEVEL = {"NIFTY": 25000.0, "BANKNIFTY": 56000.0, "RELIANCE": 1400.0, "HDFCBANK": 1000.0, "INFY": 1500.0,
                 "SBIN": 900.0}  # fmt: skip
STRIKE_STEP = {"RELIANCE": 10.0, "HDFCBANK": 10.0, "INFY": 20.0, "SBIN": 5.0}
MADE_UP_LOT = 100  # every underlying but SBIN, so the dry run shows a lot_unknown row too


def made_up_lot(underlying: str, expiry: date) -> int | None:
    return None if underlying == "SBIN" else MADE_UP_LOT


class JumpingClock:
    """Wall time (IST) and a timer that move only when something sleeps or answers."""

    def __init__(self, session: date, start: time | None = None):
        first = start or (datetime.combine(date.min, SLOTS[0]) - timedelta(minutes=5)).time()
        self.now = datetime.combine(session, first, IST)
        self.seconds = 0.0

    def wall(self) -> datetime:
        return self.now

    def timer(self) -> float:
        return self.seconds

    def sleep(self, seconds: float) -> None:
        self.now += timedelta(seconds=seconds)
        self.seconds += seconds


def near_expiry(session: date) -> date:
    """The month's last Tuesday, or next month's once it has passed (made-up, like NSE's monthly expiry)."""
    this = last_tuesday(session)
    return this if this >= session else last_tuesday(this + timedelta(days=7))


def last_tuesday(day: date) -> date:
    following = (day.replace(day=28) + timedelta(days=4)).replace(day=1)
    last = following - timedelta(days=1)
    return last - timedelta(days=(last.weekday() - 1) % 7)


class MadeUpGroww:
    """Answers the three read calls the probe makes, in the SDK's shapes."""

    EXCHANGE_NSE, SEGMENT_FNO = "NSE", "FNO"

    def __init__(self, clock: JumpingClock, session: date):
        self.clock, self.expiry = clock, near_expiry(session)

    def get_expiries(self, exchange, underlying_symbol, year):
        self.clock.sleep(CALL_SECONDS)
        return {"expiries": [self.expiry.isoformat()]}

    def get_quote(self, trading_symbol, exchange, segment):
        self.clock.sleep(CALL_SECONDS)
        level = next((v for k, v in MADE_UP_LEVEL.items() if trading_symbol.startswith(k)), 100.0)
        bid = None if trading_symbol.endswith("PE") and "INFY" in trading_symbol else level * 0.999
        return {"bid_price": bid, "offer_price": level * 1.001, "last_price": level,
                "last_trade_time": int(self.clock.wall().timestamp()) - 5}  # fmt: skip

    def get_option_chain(self, exchange, underlying, expiry_date):
        self.clock.sleep(CALL_SECONDS)
        level, step = MADE_UP_LEVEL[underlying], STRIKE_STEP[underlying]
        strikes = [level + step * k for k in range(-5, 6)]
        legs = {f"{s:g}": {kind: {"trading_symbol": f"{underlying}{s:g}{kind}", "ltp": 10.0} for kind in ("CE", "PE")}
                for s in strikes}  # fmt: skip
        return {"underlying_ltp": level, "strikes": legs}


class MadeUpResponse:
    def __init__(self, payload: dict | None, status: int = 200):
        self.status_code, self.payload = status, payload
        self.content = b"<html></html>" if payload is None else b"{}"

    def json(self):
        if self.payload is None:
            raise ValueError("not JSON")
        return self.payload


class MadeUpNse:
    """A stand-in for the requests session NSE's reader holds: the page, quote-derivative and the equity chain."""

    def __init__(self, clock: JumpingClock, session: date):
        self.clock, self.expiry, self.headers = clock, near_expiry(session), {}

    def get(self, url, params=None, timeout=None):
        self.clock.sleep(CALL_SECONDS)
        symbol = (params or {}).get("symbol", "")
        if "quote-derivative" in url:
            return MadeUpResponse(self._future(symbol))
        if "option-chain-equities" in url:
            return MadeUpResponse(self._chain(symbol))
        return MadeUpResponse(None)

    def _stamp(self) -> str:
        return self.clock.wall().strftime("%d-%b-%Y %H:%M:%S")

    def _future(self, symbol: str) -> dict:
        level = MADE_UP_LEVEL[symbol]
        kind = "Index Futures" if symbol in FUTURES[:2] else "Stock Futures"
        meta = {"instrumentType": kind, "expiryDate": f"{self.expiry:%d-%b-%Y}", "lastPrice": level}
        book = {"bid": [{"price": level - 1, "quantity": 1}], "ask": [{"price": level + 1, "quantity": 1}]}
        return {"fut_timestamp": self._stamp(), "stocks": [{"metadata": meta, "marketDeptOrderBook": book}]}

    def _chain(self, symbol: str) -> dict:
        level, step, expiry = MADE_UP_LEVEL[symbol], STRIKE_STEP[symbol], f"{self.expiry:%d-%b-%Y}"
        rows = [{"strikePrice": level + step * k, "expiryDate": expiry,
                 "CE": {"lastPrice": 10.0, "buyPrice1": 9.5, "sellPrice1": 10.5, "expiryDate": expiry},
                 "PE": {"lastPrice": 10.0, "buyPrice1": 0, "sellPrice1": 10.5, "expiryDate": expiry}}
                for k in range(-5, 6)]  # fmt: skip
        return {"records": {"underlyingValue": level, "timestamp": self._stamp(), "expiryDates": [expiry],
                            "data": rows}}  # fmt: skip
