"""Three ledgers so that "profitable" always means money actually kept (story C1, design section 8).

1. Trade ledger: each trade's gross P&L at quoted prices, the cost of the assumed worse fills (pads), every charge by
   component (from `fno.costs`, the single charges model) and the net.
2. Account ledger: trade net by month minus the desk's own operating costs (AI, data), entered as actual amounts.
3. Tax: one **assumed scenario**, not a verified tax liability: Indian financial year (April-March); base = the year's
   trade net minus operating costs in categories declared deductible; tax = rate x max(0, base); losses offset within
   the year; no carry-forward modelled. Tax never enters a research pass/fail.
"""

from __future__ import annotations

import csv
import io
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date

from ..constants import SIDE_BUY, SIDE_SELL
from ..costs import CHARGE_NAMES, order_charges_breakdown, settlement_charges_breakdown

DEFAULT_TAX_RATE_PCT = 31.2  # owner decision: 30% slab + 4% cess, on the year's net F&O profit
TAX_LABEL = "assumed scenario (30% slab + 4% cess on yearly net F&O profit), not a verified tax liability"
NO_CARRY_FORWARD = "loss shown; carry-forward to later years is not modelled"
COST_COLUMNS = ("month", "item", "category", "amount_rs", "source")
CATEGORY_COLUMNS = ("category", "deductible", "note")
CATEGORY_DEDUCTIBLE, CATEGORY_NOT_DEDUCTIBLE = "yes", "no"
TOLERANCE_RS = 0.01  # rounding allowed when ledgers are compared


@dataclass(frozen=True)
class Order:
    side: str  # SIDE_BUY or SIDE_SELL
    quoted_price: float  # the price the market showed
    units: int  # lots x lot size
    pad: float = 0.0  # rupees per unit worse than quoted (assumed slippage)
    settlement: bool = False  # True: closed by NSE's cash settlement at expiry, at intrinsic value (story E7)

    @property
    def fill_price(self) -> float:
        return self.quoted_price + self.pad if self.side == SIDE_BUY else max(self.quoted_price - self.pad, 0.0)

    def charges(self, table: dict) -> dict[str, float]:
        """Each charge on this order by component, from the one charges model (`fno.costs`): a traded order's charges
        on its fill price, or a cash settlement's charges on its intrinsic value."""
        breakdown = settlement_charges_breakdown if self.settlement else order_charges_breakdown
        return breakdown(self.fill_price, self.units, self.side, table)


@dataclass(frozen=True)
class Trade:
    trade_id: str
    closed_on: date
    orders: tuple[Order, ...]


@dataclass
class TradeLine:
    trade_id: str
    closed_on: date
    gross: float  # at quoted prices
    pads: float  # cost of the assumed worse fills
    charges: dict[str, float] = field(default_factory=dict)  # by component, on the fill prices

    @property
    def net(self) -> float:
        return self.gross - self.pads - sum(self.charges.values())


def trade_line(trade: Trade, charges_table: dict) -> TradeLine:
    sign = {SIDE_BUY: -1.0, SIDE_SELL: 1.0}
    gross = sum(sign[o.side] * o.quoted_price * o.units for o in trade.orders)
    fills = sum(sign[o.side] * o.fill_price * o.units for o in trade.orders)
    charges = dict.fromkeys(CHARGE_NAMES, 0.0)
    for order in trade.orders:
        for name, value in order.charges(charges_table).items():
            charges[name] += value
    return TradeLine(trade.trade_id, trade.closed_on, gross, gross - fills, charges)


def financial_year(day: date) -> str:
    """Indian financial year label, e.g. 31 Mar 2025 -> "2024-25", 1 Apr 2025 -> "2025-26"."""
    start = day.year if day.month >= 4 else day.year - 1
    return f"{start}-{(start + 1) % 100:02d}"


def _rows(text: str, columns: tuple[str, ...], what: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(text))
    if tuple(reader.fieldnames or ()) != columns:
        raise ValueError(f"{what} columns must be {columns}")
    rows = list(reader)
    if any(None in row or None in row.values() for row in rows):
        raise ValueError(f"{what}: a row has the wrong number of fields")
    return rows


def read_operating_costs(text: str) -> list[dict]:
    rows = _rows(text, COST_COLUMNS, "operating costs")
    for row in rows:
        float(row["amount_rs"])
        date.fromisoformat(row["month"] + "-01")
    return rows


def read_cost_categories(text: str) -> dict[str, bool]:
    """Every declared operating-cost category -> deductible or not (an undeclared category is refused later)."""
    categories = {}
    for row in _rows(text, CATEGORY_COLUMNS, "cost categories"):
        flag = row["deductible"].strip()
        if flag not in (CATEGORY_DEDUCTIBLE, CATEGORY_NOT_DEDUCTIBLE):
            raise ValueError(f"category {row['category']!r}: deductible must be yes or no, not {flag!r}")
        categories[row["category"]] = flag == CATEGORY_DEDUCTIBLE
    return categories


@dataclass
class Ledgers:
    trades: list[TradeLine]
    operating_costs: list[dict]
    categories: dict[str, bool]  # every declared category -> deductible (read_cost_categories)
    tax_rate_pct: float = DEFAULT_TAX_RATE_PCT

    def __post_init__(self):
        unknown = sorted({c["category"] for c in self.operating_costs} - set(self.categories))
        if unknown:
            raise ValueError(f"undeclared operating-cost categories {unknown}: declare each one first")

    def _deductible(self, cost: dict) -> bool:
        return self.categories[cost["category"]]

    def by_month(self) -> dict[str, dict[str, float]]:
        months: dict[str, dict[str, float]] = defaultdict(lambda: {"trade_net": 0.0, "operating_costs": 0.0})
        for line in self.trades:
            months[line.closed_on.strftime("%Y-%m")]["trade_net"] += line.net
        for cost in self.operating_costs:
            months[cost["month"]]["operating_costs"] += float(cost["amount_rs"])
        for values in months.values():
            values["account_result"] = values["trade_net"] - values["operating_costs"]
        return dict(sorted(months.items()))

    def tax_by_year(self) -> dict[str, dict]:
        years: dict[str, dict] = defaultdict(
            lambda: {"trade_net": 0.0, "operating_costs": 0.0, "deductible_costs": 0.0}
        )
        for line in self.trades:
            years[financial_year(line.closed_on)]["trade_net"] += line.net
        for cost in self.operating_costs:
            year = years[financial_year(date.fromisoformat(cost["month"] + "-01"))]
            year["operating_costs"] += float(cost["amount_rs"])
            if self._deductible(cost):
                year["deductible_costs"] += float(cost["amount_rs"])
        for values in years.values():
            values["account_result"] = values["trade_net"] - values["operating_costs"]
            values["tax_base"] = values["trade_net"] - values["deductible_costs"]
            values["tax"] = self.tax_rate_pct / 100 * max(0.0, values["tax_base"])
            values["after_tax"] = values["account_result"] - values["tax"]
            values["label"] = TAX_LABEL
            if values["tax_base"] < 0:
                values["note"] = NO_CARRY_FORWARD
        return dict(sorted(years.items()))

    def reconciles(self, months: dict | None = None, years: dict | None = None) -> bool:
        """The ledgers agree with each other and with the raw entries: all months add up to the raw trade and cost
        totals; every financial year equals the sum of its months; every tax base equals the year's trade net minus
        its deductible costs recomputed from the raw costs. `months` and `years` default to the computed tables (they
        can be passed in, e.g. to prove that a broken table is caught)."""
        months = self.by_month() if months is None else months
        years = self.tax_by_year() if years is None else years
        trade_total = sum(t.net for t in self.trades)
        cost_total = sum(float(c["amount_rs"]) for c in self.operating_costs)
        checks = [
            _close(sum(m["trade_net"] for m in months.values()), trade_total),
            _close(sum(m["operating_costs"] for m in months.values()), cost_total),
            _close(sum(m["account_result"] for m in months.values()), trade_total - cost_total),
            set(years) == {financial_year(date.fromisoformat(m + "-01")) for m in months},
        ]
        for label, year in years.items():
            in_year = [m for key, m in months.items() if financial_year(date.fromisoformat(key + "-01")) == label]
            deductible = sum(
                float(c["amount_rs"])
                for c in self.operating_costs
                if self._deductible(c) and financial_year(date.fromisoformat(c["month"] + "-01")) == label
            )
            checks += [_close(year[k], sum(m[k] for m in in_year)) for k in ("trade_net", "operating_costs")]
            checks += [
                _close(year["account_result"], sum(m["account_result"] for m in in_year)),
                _close(year["tax_base"], year["trade_net"] - deductible),
                _close(year["tax"], self.tax_rate_pct / 100 * max(0.0, year["tax_base"])),
                _close(year["after_tax"], year["account_result"] - year["tax"]),
            ]
        return all(checks)


def _close(a: float, b: float) -> bool:
    return abs(a - b) < TOLERANCE_RS
