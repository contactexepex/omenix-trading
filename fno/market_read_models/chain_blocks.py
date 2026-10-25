"""The option chain's blocks for screen 32 (story P9, W13's contract `blocks-chain.yaml`, `blocks-chain-history.yaml`),
each a pure function of the session's chain. Blocks the route asks for by a parameter are stored one page per answer,
validated against the served schema itself: rows per expiry with every strike (`chain_rows:<expiry>`; the route serves
near and band from it) and history per contract (`chain_contract:<code>`, every contract in scope: owner default, W13
x-empty)."""

from __future__ import annotations

from .blocks import CURRENCY, BlockBuilder, SessionRows, as_of
from .chain_expiries import CALL
from .chain_route import ALL
from .chain_session import ChainSession

ROWS_PAGE, CONTRACT_PAGE = "chain_rows:{expiry}", "chain_contract:{code}"  # W13's page keys (blocks-chain.yaml)
EOD_SOURCE = "NSE daily F&O file of {day}: close, settlement, open interest and its change, volume (no bid or ask)"
INDEX_SOURCE = "NSE daily index file (NIFTY 50, India VIX)"
QUOTES = {
    "status": "not_published", "started": "2026-10-13",
    "text": "The F&O tool's 3 pm recording of bid and ask (the nearest two monthly expiries, strikes within 5% of "
            "NIFTY) started on 13 Oct 2026. Its quotes appear here once the tool publishes them; until then no paper "
            "order can be priced.",
}  # fmt: skip
COMPUTED = {
    "iv": "Black-Scholes from the day's close, only when the contract traded; rate 6.5%, no dividend; calendar days to "
          "expiry / 365",
    "chance": "Risk-neutral: what the option's own price implies, not a forecast",
}  # fmt: skip
BOOKS = (
    "No F&O book holds a position: no strategy has passed testing yet, so each book records “no approved strategy” at "
    "3 pm."
)


def _chain(rows: SessionRows) -> ChainSession:
    return rows.chain


def default_expiry(chain: ChainSession) -> dict:
    """The nearest monthly expiry: the page opens on it."""
    return next(e for e in chain.expiries if e["monthly"])


class ChainUnderlyingBlock(BlockBuilder):
    page_key, served_schema = "chain_underlying", "ChainUnderlyingResponse"

    def build(self, rows: SessionRows) -> dict:
        u = _chain(rows).underlying
        return {**{k: u[k] for k in ("sym", "spot", "chg", "chg_pct", "vix")}, "as_of": as_of(rows.day)}


class ChainExpiriesBlock(BlockBuilder):
    page_key, served_schema = "chain_expiries", "ChainExpiriesResponse"

    def build(self, rows: SessionRows) -> dict:
        keys = ("expiry", "days", "monthly", "future", "stats")
        return {"as_of": as_of(rows.day), "expiries": [{k: e[k] for k in keys} for e in _chain(rows).expiries]}


class ChainRowsBlock(BlockBuilder):
    """One page per expiry with every strike in scope ("all"); the route serves near and band from it (W13)."""

    page_key, served_schema = "chain_rows", "ChainRowsResponse"

    def build(self, rows: SessionRows) -> dict:
        return self.page(rows, default_expiry(_chain(rows)))

    def pages(self, rows: SessionRows) -> dict[str, dict]:
        return {ROWS_PAGE.format(expiry=e["expiry"]): self.page(rows, e) for e in _chain(rows).expiries}

    @staticmethod
    def page(rows: SessionRows, expiry: dict) -> dict:
        return {"as_of": as_of(rows.day), "currency": CURRENCY, "lot": _chain(rows).underlying["lot"],
                "expiry": expiry["expiry"], "strikes": ALL, "rows": expiry["rows"]}  # fmt: skip


class ChainHistoryBlock(BlockBuilder):
    page_key, served_schema = "chain_history", "ChainHistoryResponse"

    def build(self, rows: SessionRows) -> dict:
        return _chain(rows).history


class ContractHistoryBlock(BlockBuilder):
    page_key, served_schema = "contract_history", "ContractHistoryResponse"

    def build(self, rows: SessionRows) -> dict:
        """The nearest monthly's ATM call (the page's first contract view)."""
        expiry = default_expiry(_chain(rows))
        atm = next(r for r in expiry["rows"] if r["strike"] == expiry["stats"]["atm"])
        return _chain(rows).contracts[atm[CALL]["code"]]

    def pages(self, rows: SessionRows) -> dict[str, dict]:
        return {CONTRACT_PAGE.format(code=code): history for code, history in sorted(_chain(rows).contracts.items())}


class ChainSourcesBlock(BlockBuilder):
    page_key, served_schema = "chain_sources", "ChainSourcesResponse"

    def build(self, rows: SessionRows) -> dict:
        chain = _chain(rows)
        source = {"eod": EOD_SOURCE.format(day=rows.day.isoformat()), "index": INDEX_SOURCE,
                  "history_from": chain.history_from.isoformat(), "as_of": as_of(rows.day)}  # fmt: skip
        return {"source": source, "quotes": QUOTES, "computed": COMPUTED, "books": BOOKS}
