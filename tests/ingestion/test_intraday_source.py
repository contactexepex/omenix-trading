"""The Groww 15-minute capture path end to end, OFFLINE (``fno/ingestion/intraday/groww_source.py``).

A fake SDK client is wrapped in the real ``ReadOnlyGroww`` guard and driven through ``GrowwIntradaySource.take``,
so the whole orchestration (index quote -> candle fallback -> future -> chains -> per-contract quotes) runs without a
single network call. This is the owner's headline ingestion path, covered genuinely with injected fakes."""

from __future__ import annotations

from datetime import date, datetime

import pytest

from fno.ingestion.intraday.expiry_plan import Expiries
from fno.ingestion.intraday.groww_source import GrowwIntradaySource
from fno.ingestion.intraday.index_reading import CANDLE_BASIS
from fno.ingestion.intraday.pacing import RatePacer
from fno.ingestion.intraday.read_only import ReadOnlyGroww, ReadOnlyViolation
from fno.shared.models import IST

MARK = datetime(2026, 10, 12, 14, 30, tzinfo=IST)
SESSION = date(2026, 10, 12)
MONTHLY = date(2026, 10, 30)


class _FakeGrowwSdk:
    """A stand-in for ``growwapi.GrowwAPI`` exposing only the read calls and constants the recorder uses."""

    EXCHANGE_NSE = "NSE"
    SEGMENT_CASH = "CASH"
    SEGMENT_FNO = "FNO"
    CANDLE_INTERVAL_MIN_1 = 1
    CANDLE_INTERVAL_MIN_15 = 15

    def __init__(self) -> None:
        self.calls: list[str] = []

    def get_quote(self, trading_symbol, exchange, segment, timeout=None):
        self.calls.append(f"quote:{trading_symbol}")
        if trading_symbol == "NIFTY":  # index quote with NO trade time -> forces the 1-minute candle fallback
            return {"last_price": 22100.0}
        if trading_symbol.endswith("FUT"):
            return {"last_price": 22150.0, "last_trade_time": 1760000000}
        return {"bid_price": 10.0, "offer_price": 11.0, "bid_quantity": 50, "offer_quantity": 75,
                "last_price": 10.5, "last_trade_time": 1760000000}  # fmt: skip

    def get_historical_candles(self, exchange, segment, groww_symbol, candle_interval, start_time, end_time,
                               timeout=None):  # fmt: skip
        self.calls.append("candles")
        return {"candles": [["2026-10-12T14:29:00", 22090.0, 22110.0, 22080.0, 22100.0, 1000, 0]]}

    def get_option_chain(self, exchange, underlying, expiry_date, timeout=None):
        self.calls.append(f"chain:{expiry_date}")
        strikes = {}
        for strike in (22000, 22100, 22200):
            strikes[str(strike)] = {
                "CE": {
                    "ltp": 100.0,
                    "open_interest": 1000,
                    "volume": 10,
                    "greeks": {"iv": 12.0},
                    "trading_symbol": f"NIFTY{strike}CE",
                },  # fmt: skip
                "PE": {
                    "ltp": 90.0,
                    "open_interest": 900,
                    "volume": 9,
                    "greeks": {"iv": 13.0},
                    "trading_symbol": f"NIFTY{strike}PE",
                },  # fmt: skip
            }
        return {"underlying_ltp": 22100.0, "strikes": strikes}


class _StubPlan:
    """Stands in for ``ExpiryPlan``: returns a fixed plan so the capture test needs no NSE history."""

    def plan(self, session: date) -> Expiries:
        return Expiries(nearest=MONTHLY, monthly=MONTHLY, chains=(MONTHLY,), check={"status": "test"})


def _source() -> tuple[GrowwIntradaySource, _FakeGrowwSdk]:
    sdk = _FakeGrowwSdk()
    client = ReadOnlyGroww(lambda: sdk)
    pacer = RatePacer(4, clock=lambda: 0.0, sleep=lambda _s: None)  # never sleeps for real
    source = GrowwIntradaySource(client, _StubPlan(), lot_size=75, clock=lambda: MARK, pacer=pacer)
    return source, sdk


def test_take_captures_index_future_chain_and_quotes() -> None:
    source, sdk = _source()
    source.prepare(SESSION)
    doc = source.take(SESSION, MARK)

    assert doc.index_level == 22100.0  # from the finished 14:29 candle (quote had no trade time)
    assert doc.index_basis == CANDLE_BASIS
    assert "candles" in sdk.calls  # the candle fallback really ran
    assert doc.future is not None and doc.future.failure == ""
    assert len(doc.chains) == 1 and doc.chains[0].failure == ""
    assert doc.expected_contracts == 6  # 3 strikes x CE/PE, all within the 6% band
    assert doc.recorded_contracts == 6  # every quote succeeded
    assert doc.two_sided_contracts == 6  # each has bid and ask
    assert doc.failures == []
    assert doc.finished_at == MARK


def test_take_is_byte_round_trippable() -> None:
    source, _ = _source()
    source.prepare(SESSION)
    doc = source.take(SESSION, MARK)
    from fno.ingestion.intraday.document import SnapshotDocument

    back = SnapshotDocument.from_bytes(doc.to_bytes())
    assert back.recorded_contracts == doc.recorded_contracts
    assert back.index_level == doc.index_level


def test_read_only_guard_blocks_non_read_calls() -> None:
    client = ReadOnlyGroww(lambda: _FakeGrowwSdk())
    assert client.EXCHANGE_NSE == "NSE"  # an allow-listed constant passes
    assert callable(client.get_quote)  # an allow-listed read call passes
    with pytest.raises(ReadOnlyViolation):
        _ = client.place_order  # a trading call never reaches the SDK
    with pytest.raises(ReadOnlyViolation):
        client.anything = 1  # the guard is immutable
