"""The Groww index-level reading rules and the snapshot document (``fno/ingestion/intraday``): the quote/candle
fallback logic and a byte round-trip. Pure functions and dataclasses; no Groww call."""

from __future__ import annotations

from datetime import datetime

from fno.ingestion.intraday.document import (
    CallRecord,
    SnapshotDocument,
    snapshot_path,
)
from fno.ingestion.intraday.index_reading import (
    CANDLE_BASIS,
    OPEN_BASIS,
    candle_reading,
    candle_start,
    candle_window,
    epoch_time,
    quote_reading,
)
from fno.shared.models import IST


def _ist(y, m, d, hh, mm, ss=0) -> datetime:
    return datetime(y, m, d, hh, mm, ss, tzinfo=IST)


def test_quote_reading_with_and_without_time() -> None:
    level, stamp = quote_reading({"last_price": 22100.0, "last_trade_time": 1760000000})
    assert level == 22100.0 and stamp is not None
    level2, stamp2 = quote_reading({"last_price": 22100.0})
    assert level2 == 22100.0 and stamp2 is None
    assert quote_reading("not a dict") == (None, None)


def test_epoch_time_seconds_and_milliseconds() -> None:
    seconds = epoch_time(1760000000)
    millis = epoch_time(1760000000000)
    assert seconds is not None and millis is not None
    assert abs((seconds - millis).total_seconds()) < 1  # same instant, different unit
    assert epoch_time(None) is None


def test_candle_window_is_five_minutes_in_ist_text() -> None:
    window = candle_window(_ist(2026, 10, 12, 14, 30, 40))
    assert window == {"start_time": "2026-10-12 14:25:40", "end_time": "2026-10-12 14:30:40"}


def test_candle_reading_uses_latest_finished_candle() -> None:
    mark = _ist(2026, 10, 12, 14, 30)
    received = _ist(2026, 10, 12, 14, 30, 40)
    payload = {"candles": [
        ["2026-10-12T14:29:00", 22090.0, 22110.0, 22080.0, 22100.0, 1000, 0],  # finished, ends 14:30:00
        ["2026-10-12T14:30:00", 22100.0, 22120.0, 22095.0, 22115.0, 500, 0],   # still forming at 14:30:40
    ]}  # fmt: skip
    level, stamp, basis = candle_reading(payload, received, mark)
    assert level == 22100.0  # close of the finished 14:29 candle
    assert stamp == _ist(2026, 10, 12, 14, 30)  # its end
    assert basis == CANDLE_BASIS


def test_candle_reading_open_at_the_0915_mark() -> None:
    mark = _ist(2026, 10, 12, 9, 15)
    received = _ist(2026, 10, 12, 9, 15, 30)
    payload = {"candles": [["2026-10-12T09:15:00", 22000.0, 22010.0, 21990.0, 22005.0, 100, 0]]}
    level, stamp, basis = candle_reading(payload, received, mark)
    assert level == 22000.0  # the open of the 09:15 candle (no session candle has finished yet)
    assert stamp == mark
    assert basis == OPEN_BASIS


def test_candle_reading_empty() -> None:
    assert candle_reading({"candles": []}, _ist(2026, 10, 12, 14, 30, 40), _ist(2026, 10, 12, 14, 30)) == (
        None,
        None,
        "",
    )


def test_candle_start_naive_time_gets_ist() -> None:
    start = candle_start("2026-10-12T09:15:00")
    assert start == _ist(2026, 10, 12, 9, 15)


def test_snapshot_document_round_trips_to_bytes() -> None:
    sent = _ist(2026, 10, 12, 14, 30)
    got = _ist(2026, 10, 12, 14, 30, 1)
    index = CallRecord("index", sent, got, {"last_price": 22100.0}, "", {})
    chain = CallRecord("chain 2026-10-30", sent, got, {"strikes": {}}, "", {"expiry": "2026-10-30"})
    quote = CallRecord("quote X", sent, got, {"last_price": 1.0}, "", {"symbol": "X"})
    doc = SnapshotDocument("groww", "NIFTY", sent.date(), sent, index, 22100.0, sent,
                           chains=[chain], quotes=[quote], expected_contracts=1)  # fmt: skip
    data = doc.to_bytes()
    assert doc.to_bytes() == data  # deterministic bytes (same document, same bytes)
    back = SnapshotDocument.from_bytes(data)
    assert back.source == "groww" and back.underlying == "NIFTY"
    assert back.index_level == 22100.0
    assert back.recorded_contracts == 1
    assert [c.name for c in back.chains] == ["chain 2026-10-30"]


def test_snapshot_path_names_mark_and_hash() -> None:
    mark = _ist(2026, 10, 12, 14, 30)
    path = snapshot_path("groww", mark.date(), mark, b"some-bytes")
    assert path.startswith("groww/derivatives/intraday-snapshots/2026/10/12/")
    assert "nifty_20261012_1430_" in path
    assert path.endswith(".json.gz")
