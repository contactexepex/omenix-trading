"""The six India blocks the W11 contract assigns to publisher fno (story P6), each a pure function of the session's
computed rows. Paged blocks (screener stocks, F&O rows) are published as the whole table, in the contract's order;
the dashboard's route filters, sorts and pages it (W11: "the route filters, sorts and pages")."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

from .fno_rows import BUILDUPS
from .stock_rows import UNIVERSE_FNO, UNIVERSE_FOLLOWED, UNIVERSE_NIFTY_500

if TYPE_CHECKING:
    from .chain_session import ChainSession
    from .flows_block import FlowsInputs
    from .forecast_lab_inputs import ForecastLabInputs
    from .frame_inputs import FrameInputs
    from .home_inputs import HomeInputs
    from .weather_inputs import WeatherInputs

CLOSE_UTC = "T10:00:00Z"  # NSE closes at 15:30 IST
CURRENCY = "INR"
PAGE = 25  # the route's default page size
UNIVERSE_ALL = "all"
STOCK_KEYS = ("s", "n", "g", "p", "d1", "w1", "m1", "m3", "y1", "h", "l", "v", "va", "dl", "r", "u")
QUOTE_KEYS = ("d1", "w1", "m1", "m3", "y1", "hi52", "lo52")


@dataclass(frozen=True)
class SessionRows:
    """One session's computed rows, every block's only input."""

    day: date
    stocks: list[dict]
    fno: list[dict]
    indices: list[dict]
    industries: list[dict]
    chain: ChainSession | None = None  # the NIFTY option chain (P9)
    home: HomeInputs | None = None  # the F&O books and approvals for Home (P10)
    frame: FrameInputs | None = None  # the session the reader acts on next (P10, India's band)
    flows: FlowsInputs | None = None  # the big investors' flows (P8)
    weather: WeatherInputs | None = None  # M1's weather records for the session (P2a)
    score_reports: list[dict] | None = None  # G4's daily score reports up to the session (P2, forecast history)
    forecast_lab: ForecastLabInputs | None = None  # G4's latest report and the session's forecast records (P2b)


class BlockBuilder(ABC):
    page_key: str  # the read model's page (W11 x-read-model)
    stored_schema: str | None = None  # W11 x-stored: the shape this repository stores, where the route serves another
    served_schema: str | None = None  # the W11 response the route serves from the stored payload alone (None: merged)

    @abstractmethod
    def build(self, rows: SessionRows) -> dict:
        """The block's stored payload for the session (a paged block: the whole table)."""

    def held(self, previous: dict, rule: str) -> dict | None:
        """Story P11: the page to publish while this block is held (`PageHeld`), from the previous publication's
        payload: unchanged by default (a page that stays true for its own session); None for no row (a page whose old
        payload would state what the rule says is no longer true)."""
        return previous

    def served(self, payload: dict) -> dict:
        """The payload the route serves from the stored one by default (a paged block: its first page)."""
        return payload

    def pages(self, rows: SessionRows) -> dict[str, dict]:
        """Page key -> stored payload: one page, unless the route asks for the block by a parameter (P9)."""
        return {self.page_key: self.build(rows)}

    def inputs(self, rows: SessionRows) -> list:
        """The archived copies the block read where more than one could serve a day (P8's flows); recorded with the
        publication, outside the contract's row (it has no field for them)."""
        return []


def as_of(day: date) -> str:
    return day.isoformat() + CLOSE_UTC


def universe_counts(rows: list[dict]) -> dict:
    """The screener's day, tabs, tiles and chips, and the Markets breadth, over one universe's rows."""
    up, down = sum(1 for r in rows if (r["d1"] or 0) > 0), sum(1 for r in rows if (r["d1"] or 0) < 0)
    return {
        "n": len(rows), "up": up, "down": down, "flat": len(rows) - up - down,
        "high": sum(1 for r in rows if r["h"] and r["p"] >= r["h"]),
        "near_high": sum(1 for r in rows if r["h"] and r["p"] >= r["h"] * 0.98),
        "low": sum(1 for r in rows if r["l"] and r["p"] <= r["l"]),
        "near_low": sum(1 for r in rows if r["l"] and r["p"] <= r["l"] * 1.02),
        "up_1m": sum(1 for r in rows if (r["m1"] or 0) > 0),
        "screens": {
            "movers": sum(1 for r in rows if abs(r["d1"] or 0) >= 5),
            "volume": sum(1 for r in rows if (r["va"] or 0) >= 5e4 and r["v"] >= 3 * r["va"]),
            "trend": sum(1 for r in rows if (r["m1"] or 0) >= 10),
            "fall": sum(1 for r in rows if (r["m1"] or 0) <= -10),
            "oversold": sum(1 for r in rows if r["r"] is not None and r["r"] < 30),
            "delivery": sum(1 for r in rows if (r["dl"] or 0) >= 70 and (r["va"] or 0) >= 1e5),
        },
    }  # fmt: skip


def in_universe(rows: list[dict], universe: str) -> list[dict]:
    return [r for r in rows if universe == UNIVERSE_ALL or universe in r["u"]]


class ScreenerSummaryBlock(BlockBuilder):
    page_key, served_schema = "screener_summary", "ScreenerSummaryIndiaResponse"

    def build(self, rows: SessionRows) -> dict:
        universes = (UNIVERSE_ALL, UNIVERSE_NIFTY_500, UNIVERSE_FNO, UNIVERSE_FOLLOWED)
        stocks = rows.stocks
        return {"as_of": as_of(rows.day), "universes": {u: universe_counts(in_universe(stocks, u)) for u in universes}}


class PagedBlock(BlockBuilder):
    """A whole table stored; the route serves pages of it (W11 2.4: page_size at most 100)."""

    def served(self, payload: dict) -> dict:
        return default_page(payload)


class ScreenerStocksBlock(PagedBlock):
    page_key, stored_schema = "screener_stocks", "ScreenerStocksTableIndia"
    served_schema = "ScreenerStocksIndiaResponse"

    def build(self, rows: SessionRows) -> dict:
        """Every stock row, by value traded (the default order)."""
        table = sorted(rows.stocks, key=lambda r: r["p"] * r["v"], reverse=True)
        return {"as_of": as_of(rows.day), "currency": CURRENCY, "total": len(table),
                "rows": [{k: r[k] for k in STOCK_KEYS} for r in table]}  # fmt: skip


class FnoSummaryBlock(BlockBuilder):
    page_key, served_schema = "fno_screener_summary", "FnoScreenerSummaryResponse"

    def build(self, rows: SessionRows) -> dict:
        fno = rows.fno
        return {
            "as_of": as_of(rows.day), "n": len(fno), "expiry": min(r["x"] for r in fno),
            "buildups": {k: sum(1 for r in fno if r["b"] == k) for k in BUILDUPS},
            "screens": {
                "ivhigh": sum(1 for r in fno if (r["ivr"] or 0) >= 80),
                "ivlow": sum(1 for r in fno if r["ivr"] is not None and r["ivr"] <= 20),
                "oiup": sum(1 for r in fno if (r["oc"] or 0) >= 5),
                "index": sum(1 for r in fno if r["kind"] == "index"),
            },
        }  # fmt: skip


class FnoRowsBlock(PagedBlock):
    page_key, stored_schema, served_schema = "fno_screener_rows", "FnoScreenerTable", "FnoScreenerRowsResponse"

    def build(self, rows: SessionRows) -> dict:
        """Every underlying, by futures open interest in rupees (the default order)."""
        table = sorted(rows.fno, key=lambda r: -(r["oi"] * r["fut"]))
        return {"as_of": as_of(rows.day), "currency": CURRENCY, "total": len(table), "rows": table}


class IndicesBlock(BlockBuilder):
    page_key, served_schema = "overview_indices", "OverviewIndicesIndiaResponse"

    def build(self, rows: SessionRows) -> dict:
        return {"indices": [quote(r) for r in rows.indices if r["group"] != "sector"]}


class SectorsBlock(BlockBuilder):
    page_key, served_schema = "overview_sectors", "IndiaSectorsResponse"

    def build(self, rows: SessionRows) -> dict:
        sectors = [quote(r) for r in rows.indices if r["group"] == "sector"]
        return {"indices": sectors, "industries": rows.industries}


def default_page(table: dict, rows: list[dict] | None = None, total: int | None = None, size: int = PAGE) -> dict:
    """The route's first page over a published table (its default order unless `rows` gives another)."""
    rows = table["rows"] if rows is None else rows
    return {"as_of": table["as_of"], "currency": table["currency"], "total": len(rows) if total is None else total,
            "page": 1, "page_size": size, "rows": rows[:size]}  # fmt: skip


def quote(row: dict) -> dict:
    keys = {k: row[k] for k in QUOTE_KEYS}
    figures = {k: row[k] for k in ("pe", "pb", "dy")}
    return {"name": row["name"], "kind": row["group"], "close": row["close"], "as_of": row["as_of"], **keys,
            "closes": row["closes"], **figures}  # fmt: skip
