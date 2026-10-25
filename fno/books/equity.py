"""Positions and the three account measures, defined once here for E1 and reused by the risk manager (story C2):

- **closed equity** = starting cash + net P&L of closed trades (net of pads and every charge);
- **marked equity** = closed equity + open trades valued at the mid of valid quotes (or the last valid mark, flagged
  stale); equal to cash + the marked value of open positions;
- **available cash** = min(cash, marked equity) - margin blocked - premium reserved for pending orders (decided 13 Oct
  2026 in place of C2's first text "marked equity - ...", which counted a bought option's premium as spendable twice;
  margin and pending premium are inputs, from C2 and E4).

A missing mark for an open contract is an error: a price is never invented.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from ..accounting.ledgers import Trade
from .fills import Fill


class MissingMark(ValueError):
    """An open contract has no mark, so the account cannot be valued."""


@dataclass(frozen=True)
class Mark:
    price: float  # mid of valid quotes, or the last valid mark
    stale: bool = False  # True when it is the last valid mark, not today's


@dataclass
class TradePosition:
    trade_id: str
    fills: list[Fill] = field(default_factory=list)
    units: dict[str, int] = field(default_factory=dict)  # contract -> signed units (long +, short -)
    cash_flow: float = 0.0  # premium received minus paid, minus charges, so far
    closed_on: date | None = None  # the day the last leg went flat

    @property
    def is_open(self) -> bool:
        return self.closed_on is None

    def add(self, fill: Fill) -> None:
        self.fills.append(fill)
        self.units[fill.contract] = self.units.get(fill.contract, 0) + fill.signed_units
        self.cash_flow += fill.amount
        self.closed_on = fill.filled_at.date() if not any(self.units.values()) else None

    def as_ledger_trade(self) -> Trade:
        """The closed trade in the cost accountant's form (C1), so the three ledgers read the same fills."""
        return Trade(self.trade_id, self.closed_on, tuple(f.order for f in self.fills))


def trade_positions(fills: list[Fill]) -> dict[str, TradePosition]:
    trades: dict[str, TradePosition] = {}
    for fill in fills:
        trades.setdefault(fill.trade_id, TradePosition(fill.trade_id)).add(fill)
    return trades


@dataclass(frozen=True)
class AccountState:
    capital: float  # the opening plus top-ups in force (story E1b): never profit
    cash: float
    closed_equity: float
    open_value: float  # marked value of open positions (long +, short -)
    marked_equity: float
    margin_blocked: float
    premium_reserved: float
    open_trades: int
    stale_marks: tuple[str, ...]

    @property
    def available_cash(self) -> float:
        """min(cash, marked equity) - margin blocked - premium reserved: a bought option's premium is not spendable
        again (cash is lower), and a short option's unrealised loss is not spendable either (marked equity is lower)."""
        return min(self.cash, self.marked_equity) - self.margin_blocked - self.premium_reserved


def account_state(
    capital: float,
    fills: list[Fill],
    marks: dict[str, Mark],
    margin_blocked: float = 0.0,
    premium_reserved: float = 0.0,
) -> AccountState:
    trades = trade_positions(fills).values()
    closed_equity = capital + sum(t.cash_flow for t in trades if not t.is_open)
    open_cash_flow, open_value, stale = 0.0, 0.0, set()
    for trade in (t for t in trades if t.is_open):
        open_cash_flow += trade.cash_flow
        for contract, units in trade.units.items():
            if not units:
                continue
            if contract not in marks:
                raise MissingMark(f"no mark for open contract {contract} (trade {trade.trade_id})")
            open_value += units * marks[contract].price
            if marks[contract].stale:
                stale.add(contract)
    cash = capital + sum(f.amount for f in fills)
    return AccountState(
        capital,
        cash,
        closed_equity,
        open_value,
        closed_equity + open_cash_flow + open_value,
        margin_blocked,
        premium_reserved,
        sum(t.is_open for t in trades),
        tuple(sorted(stale)),
    )


def unmarked_state(capital: float, fills: list[Fill]) -> dict:
    """What can be stated without marks (for the positions file): cash, closed equity and the open legs."""
    trades = trade_positions(fills)
    return {
        "cash_rs": capital + sum(f.amount for f in fills),
        "closed_equity_rs": capital + sum(t.cash_flow for t in trades.values() if not t.is_open),
        "open_trades": [
            {
                "trade_id": t.trade_id,
                "legs": {c: u for c, u in sorted(t.units.items()) if u},
                "cash_flow_rs": t.cash_flow,
            }
            for t in trades.values()
            if t.is_open
        ],
        "closed_trades": [
            {"trade_id": t.trade_id, "closed_on": t.closed_on.isoformat(), "net_rs": t.cash_flow}
            for t in trades.values()
            if not t.is_open
        ],
    }
