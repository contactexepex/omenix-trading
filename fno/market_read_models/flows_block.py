"""India's big-investor flows for Markets 34 (story P8, contract 2.5: `Flows`, page `flows`, publisher fno): FII/FPI
and DII cash-market values per session (NSE, provisional) and NSDL's FPI equity net, each series on its own, with the
period totals published only when the days cover the whole period (W11's rule, judge 27)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from .blocks import CURRENCY, BlockBuilder, SessionRows
from .flows_files import CashFlows, FlowSide

PERIODS = {"d1": 1, "w1": 5, "m1": 21, "m3": 63, "y1": 250}  # sessions per period switch value
DAYS_KEPT = 250


@dataclass(frozen=True)
class FlowsCopy:
    """The archived copy a session's figures were read from (judge 66: each publication records it)."""

    dataset: str
    session: date  # the session the copy covers
    filed_on: date  # the IST day it was fetched (the archive's folder); the time of day is not kept
    sha256: str


@dataclass(frozen=True)
class FlowsInputs:
    cash: list[CashFlows]  # one per session, the latest copy of each, sessions up to the published one
    nsdl: list[tuple[date, float]]  # (reporting day, FPI equity net)
    sessions: list[date]  # the NSE sessions up to the published one, the last 250, oldest first
    copies: list[FlowsCopy] = field(default_factory=list)  # the copy behind each session's figures, both series


class FlowsBlock(BlockBuilder):
    page_key, served_schema = "flows", "FlowsResponse"

    def build(self, rows: SessionRows) -> dict:
        flows = rows.flows
        kept = set(flows.sessions[-DAYS_KEPT:])
        cash = [c for c in flows.cash if c.day in kept]
        return {
            "currency": CURRENCY,
            "totals": {key: period_total(cash, flows.sessions[-n:], n) for key, n in PERIODS.items()},
            "days": [{"date": c.day.isoformat(), "fii": _side(c.fii), "dii": _side(c.dii)} for c in cash],
            "nsdl": [{"date": d.isoformat(), "net": net} for d, net in flows.nsdl if d in kept],
        }

    def inputs(self, rows: SessionRows) -> list[FlowsCopy]:
        kept = set(rows.flows.sessions[-DAYS_KEPT:])
        return [c for c in rows.flows.copies if c.session in kept]


def period_total(cash: list[CashFlows], sessions: list[date], n: int) -> dict:
    """The net of each series over the period's sessions, only when every one of them has data."""
    in_period = [c for c in cash if c.day in set(sessions)]
    complete = len(sessions) == n and len(in_period) == n
    fii = round(sum(c.fii.net for c in in_period), 2) if complete else None
    dii = round(sum(c.dii.net for c in in_period), 2) if complete else None
    return {"days_in_period": n, "days": len(in_period), "complete": complete, "fii": fii, "dii": dii}


def _side(side: FlowSide) -> dict:
    return {"buy": side.buy, "sell": side.sell, "net": side.net, "provisional": True}  # NSE's same-day figures
