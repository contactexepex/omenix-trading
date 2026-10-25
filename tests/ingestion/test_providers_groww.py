"""Groww provider parse functions (``fno/ingestion/providers/groww.py``): the raw-response parsers and the expiry
list, exercised with canned payloads and a fake API client. Never signs in, never reaches Groww."""

from __future__ import annotations

from datetime import date, datetime

import pytest

from fno.ingestion.providers.groww import (
    has_groww_credentials,
    listed_expiries,
    parse_groww_chain,
    parse_groww_quote_book,
)
from fno.shared.constants import ENV_GROWW_ACCESS_TOKEN, ENV_GROWW_API_KEY, ENV_GROWW_TOTP_SECRET

TODAY = date(2026, 10, 12)
EXPIRY = date(2026, 10, 30)

CHAIN_RESPONSE = {
    "payload": {
        "underlying_ltp": 22100.5,
        "strikes": {
            "22000": {
                "CE": {
                    "ltp": 180.0,
                    "open_interest": 120000,
                    "volume": 5000,
                    "greeks": {"iv": 12.5},
                    "trading_symbol": "NIFTY26O3022000CE",
                },  # fmt: skip
                "PE": {
                    "ltp": 90.0,
                    "open_interest": 90000,
                    "volume": 4000,
                    "greeks": {"iv": 13.1},
                    "trading_symbol": "NIFTY26O3022000PE",
                },  # fmt: skip
            },
            "22100": {
                "CE": {"ltp": 120.0, "open_interest": 80000, "volume": 3000, "greeks": {"iv": 12.0}},
            },
        },
    }
}


class _FakeGrowwApi:
    """Only what ``listed_expiries`` reads: the exchange constant and ``get_expiries``."""

    EXCHANGE_NSE = "NSE"

    def __init__(self, by_year: dict[int, object]):
        self._by_year = by_year

    def get_expiries(self, exchange: str, underlying_symbol: str, year: int):
        result = self._by_year[year]
        if isinstance(result, Exception):
            raise result
        return {"expiries": result}


def test_parse_groww_chain() -> None:
    at = datetime(2026, 10, 12, 15, 0)
    chain = parse_groww_chain(CHAIN_RESPONSE, "nifty", EXPIRY, lot_size=75, at=at)
    assert chain.underlying == "NIFTY"
    assert chain.spot == 22100.5
    assert chain.lot_size == 75
    assert chain.source == "groww"
    ce = chain.get(22000, "CE")
    assert ce is not None and ce.ltp == 180.0 and ce.oi == 120000 and ce.iv == 12.5
    assert ce.symbol == "NIFTY26O3022000CE"
    assert chain.get(22100, "PE") is None  # only a CE leg was present at 22100
    assert set(chain.strikes()) == {22000.0, 22100.0}


def test_parse_quote_book_from_fields() -> None:
    payload = {"bid_price": 179.5, "offer_price": 180.5, "bid_quantity": 750, "offer_quantity": 1500,
               "last_price": 180.0, "last_trade_time": 1760000000}  # fmt: skip
    book = parse_groww_quote_book("NIFTY26O3022000CE", payload)
    assert book.symbol == "NIFTY26O3022000CE"
    assert book.bid == 179.5 and book.ask == 180.5
    assert book.book_source == "fields"
    assert book.last_trade_time is not None
    assert len(book.raw_sha256) == 64


def test_parse_quote_book_from_depth_fallback() -> None:
    payload = {"depth": {"buy": [{"price": 100.0, "quantity": 50}], "sell": [{"price": 101.0, "quantity": 60}]},
               "last_price": 100.5}  # fmt: skip
    book = parse_groww_quote_book("SYM", payload)
    assert book.bid == 100.0 and book.ask == 101.0
    assert book.book_source == "depth"


def test_parse_quote_book_no_book() -> None:
    book = parse_groww_quote_book("SYM", {"last_price": 10.0})
    assert book.bid is None and book.ask is None and book.book_source == ""


def test_listed_expiries_filters_past_and_merges_years() -> None:
    api = _FakeGrowwApi({
        2026: ["2026-10-09", "2026-10-30", "2026-11-27"],  # 10-09 is before TODAY and must drop
        2027: ["2027-01-29"],
    })  # fmt: skip
    assert listed_expiries(api, "NIFTY", TODAY) == [date(2026, 10, 30), date(2026, 11, 27), date(2027, 1, 29)]


def test_listed_expiries_tolerates_next_year_refusal() -> None:
    api = _FakeGrowwApi({2026: ["2026-10-30"], 2027: ValueError("Year cannot be in the future")})
    assert listed_expiries(api, "NIFTY", TODAY) == [date(2026, 10, 30)]


def test_has_groww_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    assert has_groww_credentials() is False  # conftest blanked everything
    monkeypatch.setenv(ENV_GROWW_API_KEY, "key-only")
    assert has_groww_credentials() is False  # a key alone cannot sign in
    monkeypatch.setenv(ENV_GROWW_TOTP_SECRET, "seed")
    assert has_groww_credentials() is True  # key + TOTP seed
    monkeypatch.delenv(ENV_GROWW_API_KEY)
    monkeypatch.delenv(ENV_GROWW_TOTP_SECRET)
    monkeypatch.setenv(ENV_GROWW_ACCESS_TOKEN, "ready-token")
    assert has_groww_credentials() is True
