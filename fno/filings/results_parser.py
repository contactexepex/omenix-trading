"""Turns a results XBRL file into one row of figures (story A12). SEBI's taxonomies name the same figure differently
for companies (Ind AS), banks and others, so each figure lists the names it is read from, first present wins.

Which period each figure covers:
- profit and loss (revenue, profit before tax, net profit, EPS): the quarter (the shortest period ending on the
  reporting date);
- cash flow: the year to date (the longest period ending on the reporting date: six months in a September filing,
  twelve in a March one); `cash_flow_months` says which;
- balance sheet (debt, cash, assets, equity): the reporting date itself.
A figure the file does not hold is None: never guessed, never taken from another period.

Banks report total income (interest earned plus other income) where companies report revenue from operations;
insurers' names (profit, EPS) come last in each list.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from .xbrl import Fact, Period, read_facts

REVENUE = ("RevenueFromOperations", "Income")
PROFIT_BEFORE_TAX = ("ProfitBeforeTax", "ProfitLossFromOrdinaryActivitiesBeforeTax", "ProfitLossBeforeTax")
NET_PROFIT = ("ProfitLossForPeriod", "ProfitLossForThePeriod", "ProfitLossAfterTaxAndExtraordinaryItems")
EPS = (
    "BasicEarningsLossPerShareFromContinuingAndDiscontinuedOperations",
    "BasicEarningsLossPerShareFromContinuingOperations",
    "BasicEarningsPerShareAfterExtraordinaryItems",
    "BasicAndDilutedEPSAfterExtraordinaryItemsNetOfTaxExpenseForThePeriodNotToBeAnnualized",  # insurers
)
DEBT_PARTS = ("BorrowingsCurrent", "BorrowingsNoncurrent")  # Ind AS companies split borrowings
DEBT_TOTAL = ("Borrowings",)  # banks and financial companies report one total
CASH = ("CashAndCashEquivalents", "CashAndCashEquivalentsCashFlowStatement")
TOTAL_ASSETS = ("Assets",)
EQUITY = ("Equity", "EquityAttributableToOwnersOfParent")
EQUITY_PARTS = ("Capital", "ReservesAndSurplus")  # banks report share capital and reserves, not a total
OPERATING_CASH_FLOW = ("CashFlowsFromUsedInOperatingActivities",)
INVESTING_CASH_FLOW = ("CashFlowsFromUsedInInvestingActivities",)
FINANCING_CASH_FLOW = ("CashFlowsFromUsedInFinancingActivities",)
REPORTING_END = "DateOfEndOfReportingPeriod"
DAYS_PER_MONTH = 30.44


@dataclass(frozen=True)
class ResultFigures:
    period_end: date
    revenue: Decimal | None = None
    profit_before_tax: Decimal | None = None
    net_profit: Decimal | None = None
    eps: Decimal | None = None
    total_debt: Decimal | None = None
    cash: Decimal | None = None
    total_assets: Decimal | None = None
    equity: Decimal | None = None
    operating_cash_flow: Decimal | None = None
    investing_cash_flow: Decimal | None = None
    financing_cash_flow: Decimal | None = None
    cash_flow_months: int | None = None

    @property
    def has_balance_sheet(self) -> bool:
        return self.total_assets is not None

    @property
    def has_cash_flow(self) -> bool:
        return self.operating_cash_flow is not None


def parse_results(data: bytes, period_end: date | None = None) -> ResultFigures:
    """The figures of one results XBRL file; `period_end` when the file does not state its reporting date."""
    facts = read_facts(data)
    end = _reporting_end(facts) or period_end
    if end is None:
        raise ValueError("the file states no reporting date")
    durations = sorted({f.period for f in facts if f.period.end == end and f.period.start}, key=lambda p: p.days)
    quarter = durations[0] if durations else None
    to_date = durations[-1] if durations else None
    on_day = Period(None, end)
    cash_flow = _first(facts, OPERATING_CASH_FLOW, to_date)
    return ResultFigures(
        period_end=end,
        revenue=_first(facts, REVENUE, quarter),
        profit_before_tax=_first(facts, PROFIT_BEFORE_TAX, quarter),
        net_profit=_first(facts, NET_PROFIT, quarter),
        eps=_first(facts, EPS, quarter),
        total_debt=_debt(facts, on_day),
        cash=_first(facts, CASH, on_day),
        total_assets=_first(facts, TOTAL_ASSETS, on_day),
        equity=_either(_first(facts, EQUITY, on_day), _sum(facts, EQUITY_PARTS, on_day)),
        operating_cash_flow=cash_flow,
        investing_cash_flow=_first(facts, INVESTING_CASH_FLOW, to_date),
        financing_cash_flow=_first(facts, FINANCING_CASH_FLOW, to_date),
        cash_flow_months=round(to_date.days / DAYS_PER_MONTH) if cash_flow is not None else None,
    )


def _reporting_end(facts: list[Fact]) -> date | None:
    ends = [f.text for f in facts if f.name == REPORTING_END and f.text]
    return date.fromisoformat(ends[0][:10]) if ends else None


def _value(facts: list[Fact], name: str, period: Period | None) -> Decimal | None:
    for fact in facts:
        if fact.name == name and fact.period == period:
            try:
                return Decimal(fact.text)
            except InvalidOperation:
                return None
    return None


def _first(facts: list[Fact], names: tuple[str, ...], period: Period | None) -> Decimal | None:
    for name in names:
        value = _value(facts, name, period)
        if value is not None:
            return value
    return None


def _sum(facts: list[Fact], names: tuple[str, ...], period: Period) -> Decimal | None:
    """The sum of the parts the file holds; None when it holds none of them."""
    parts = [v for v in (_value(facts, n, period) for n in names) if v is not None]
    return sum(parts, Decimal(0)) if parts else None


def _debt(facts: list[Fact], on_day: Period) -> Decimal | None:
    return _either(_sum(facts, DEBT_PARTS, on_day), _first(facts, DEBT_TOTAL, on_day))


def _either(first: Decimal | None, second: Decimal | None) -> Decimal | None:
    return first if first is not None else second
