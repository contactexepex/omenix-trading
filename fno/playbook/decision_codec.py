"""JSON form of what D2's evaluation reads (story D3): the market (C2's quotes and futures) and a risk book (E1's
account state, open trades, closed equity, owner restarts). Every value round-trips exactly (floats as JSON numbers),
so a replay rebuilds the same objects the live run used."""

from __future__ import annotations

from dataclasses import asdict
from datetime import date

from ..books.equity import AccountState
from ..research_data.panel_reader import FutureQuote
from ..risk.inputs import ContractQuote, Market, OpenTrade, RiskBook, SessionTrade, TradeTerms


def market_to_json(market: Market) -> dict:
    return {
        "day": market.day.isoformat(),
        "spot": market.spot,
        "rate": market.rate,
        "quotes": {
            contract: {
                "strike": q.strike,
                "kind": q.kind,
                "expiry": q.expiry.isoformat(),
                "mid": q.mid,
                "iv": q.iv,
                "stale": q.stale,
            }  # fmt: skip
            for contract, q in sorted(market.quotes.items())
        },
        "futures": {
            e.isoformat(): {"close": f.close, "settle": f.settle, "volume": f.volume, "open_interest": f.open_interest}
            for e, f in sorted(market.futures.items())
        },
    }


def market_from_json(data: dict) -> Market:
    quotes = {
        contract: ContractQuote(q["strike"], q["kind"], date.fromisoformat(q["expiry"]), q["mid"], q["iv"], q["stale"])
        for contract, q in data["quotes"].items()
    }
    futures = {
        date.fromisoformat(e): FutureQuote(
            date.fromisoformat(e), f["close"], f["settle"], f["volume"], f["open_interest"]
        )
        for e, f in data["futures"].items()
    }
    return Market(date.fromisoformat(data["day"]), data["spot"], data["rate"], quotes, futures)


def book_to_json(book: RiskBook) -> dict:
    return {
        "name": book.name,
        "state": {**asdict(book.state), "stale_marks": list(book.state.stale_marks)},
        "open_trades": [
            {
                "trade_id": t.trade_id,
                "terms": asdict(t.terms),
                "units": dict(sorted(t.units.items())),
                "cash_flow": t.cash_flow,
            }  # fmt: skip
            for t in book.open_trades
        ],
        "session_trades": _session_to_json(book.session_trades),
        "closed_equity": [[d.isoformat(), value] for d, value in book.closed_equity],
        "restarts": [d.isoformat() for d in book.restarts],
    }


def _session_to_json(trades: tuple[SessionTrade, ...] | None) -> list | None:
    if trades is None:
        return None
    return [
        {"trade_id": t.trade_id, "states": [[dict(sorted(units.items())), cash] for units, cash in t.states]}
        for t in trades
    ]


def _session_from_json(rows: list | None) -> tuple[SessionTrade, ...] | None:
    """None in records written before C5: the new-risk cap then refuses, never guesses."""
    if rows is None:
        return None
    return tuple(SessionTrade(r["trade_id"], tuple((units, cash) for units, cash in r["states"])) for r in rows)


def book_from_json(data: dict) -> RiskBook:
    state = AccountState(**{**data["state"], "stale_marks": tuple(data["state"]["stale_marks"])})
    trades = tuple(
        OpenTrade(t["trade_id"], TradeTerms(**t["terms"]), t["units"], t["cash_flow"]) for t in data["open_trades"]
    )
    closed = tuple((date.fromisoformat(d), value) for d, value in data["closed_equity"])
    restarts = tuple(date.fromisoformat(d) for d in data["restarts"])
    return RiskBook(data["name"], state, trades, closed, restarts, _session_from_json(data.get("session_trades")))
