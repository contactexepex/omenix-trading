"""Against doing nothing, after tax (story S6 section 4; S1 `do_nothing_benchmark`; owner, 15 Oct 2026, "Shown +
real-money gate"). Capital tied at the previous session's close earns the NIFTY 50 fund's change to this close (the
"Nifty 50" closing change plus its trailing dividend yield, less the expense ratio) and the cash rate for the calendar
days between. View (a) compares per rupee-day of capital tied (RM1's gate); view (b) the whole account, idle cash at
the cash rate. A point comparison with no interval. Every tax figure is the owner's scenario, an assumption until
verified, and each simplification leans against the book: the fund keeps its exemption, F&O losses carry nothing
forward, and the AI cost earns no tax shield."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date

from .series import DailySeries, rupees

CASH_PLACEHOLDER = "placeholder until the S1 freeze sets the 91-day T-bill yield"
TAX_LABEL = "the owner's tax scenario, not a tax determination; checked before RM1"
INDEX_LABEL = "approximate total return (trailing dividend yield)"
POINT = "point comparison with no interval (response 144 item 24)"
NO_CAPITAL, NO_INDEX, NO_CAPITAL_RECORDED = "no capital tied", "index day missing: {day}", "no capital recorded: {ids}"
BEFORE_AI = "before AI cost: AI cost unknown, no verdict"


@dataclass(frozen=True)
class IndexDay:
    close: float
    dividend_yield: float | None  # percent a year, NSE's "Div Yield"


@dataclass(frozen=True)
class Terms:
    """S1's numbers: the owner's; the cash rate is the latest 91-day T-bill yield on the S1 freeze date (owner, 16 Oct
    2026), set with PROTOCOL.md on that day; the tax rates are the owner's scenario, not a tax determination."""

    account_rs: float
    cash_rate: float = 0.055  # a year; set on the freeze day with PROTOCOL.md (a test pins the two), labelled
    cash_rate_basis: str = CASH_PLACEHOLDER  # at the freeze: "91-day T-bill, RBI auction of <date>"
    fo_tax: float = 0.312  # each financial year's positive F&O net, no loss carried forward
    fund_short_tax: float = 0.208  # the fund held under 12 months (20% + 4% cess)
    fund_long_tax: float = 0.13  # 12 months or more (12.5% + 4% cess), above the exemption
    fund_exemption_rs: float = 125_000.0
    cash_tax: float = 0.312  # a liquid fund at slab
    expense: float = 0.0005  # the fund's expense ratio a year


def financial_year(day: date) -> int:
    return day.year if day.month >= 4 else day.year - 1


def fo_after_tax(series: DailySeries, rate: float) -> float:
    """Each financial year's net taxed apart (31 March splits it), a losing year untaxed and nothing carried forward."""
    years: dict[int, float] = {}
    for day, net in zip(series.days, series.net, strict=True):
        years[financial_year(day)] = years.get(financial_year(day), 0.0) + net
    return sum(net - rate * max(net, 0.0) for net in years.values())


def fund_after_tax(gain: float, first: date, last: date, terms: Terms) -> float:
    """The fund treated as sold at the section's last session, its gain taxed once; a loss untaxed."""
    long = last >= _one_year_after(first)
    taxable = max(gain - terms.fund_exemption_rs, 0.0) if long else max(gain, 0.0)
    return gain - (terms.fund_long_tax if long else terms.fund_short_tax) * taxable


def _one_year_after(day: date) -> date:
    return day.replace(year=day.year + 1, day=28) if (day.month, day.day) == (2, 29) else day.replace(year=day.year + 1)


@dataclass(frozen=True)
class Growth:
    """The fund's and cash's gain on a capital path, before tax, or why it cannot be computed."""

    fund: float = 0.0
    cash: float = 0.0
    reason: str = ""


class DoNothing:
    def __init__(self, index: Callable[[date], IndexDay | None], terms: Terms, unavailable: str = ""):
        """`unavailable` names why the index files cannot be read at all (e.g. Drive settings missing): every view then
        says so, instead of reporting each day as missing."""
        self.index, self.terms, self.unavailable = index, terms, unavailable

    def growth(self, days: Sequence[date], capital: Sequence[float]) -> Growth:
        """Capital at each previous close earns the fund's and cash's return to the next session."""
        fund = cash = 0.0
        for i in range(1, len(days)):
            before, after = self.index(days[i - 1]), self.index(days[i])
            missing = (
                days[i - 1] if before is None or before.dividend_yield is None else days[i] if after is None else None
            )
            if missing is not None:
                return Growth(reason=NO_INDEX.format(day=missing.isoformat()))
            span = (days[i] - days[i - 1]).days
            ret = after.close / before.close - 1 + (before.dividend_yield / 100 - self.terms.expense) * span / 365
            fund += capital[i - 1] * ret
            cash += capital[i - 1] * self.terms.cash_rate * span / 365
        return Growth(fund, cash)

    def compare(
        self, series: DailySeries, capital: Sequence[float], ai_cost: float | None, unrecorded: Sequence[str]
    ) -> dict:
        """Views (a) and (b) for one section: `capital` is the capital tied at each session's close (S2's basis)."""
        terms = self.terms
        book = fo_after_tax(series, terms.fo_tax) - (ai_cost or 0.0)
        label = {"tax": TAX_LABEL, "index": INDEX_LABEL, "comparison": POINT, "cash_rate": terms.cash_rate,
                 "cash_rate_basis": terms.cash_rate_basis}  # fmt: skip
        if self.unavailable:
            return {**label, "view_a": _refused(self.unavailable), "view_b": _refused(self.unavailable)}
        return {**label, "view_a": self._view_a(series, capital, book, ai_cost, unrecorded),
                "view_b": self._view_b(series, capital, book, ai_cost, unrecorded)}  # fmt: skip

    def _view_a(self, series, capital, book: float, ai_cost: float | None, unrecorded) -> dict:
        capital_days = sum(capital)
        if unrecorded:
            return _refused(NO_CAPITAL_RECORDED.format(ids=", ".join(unrecorded)))
        if capital_days <= 0:
            return _refused(NO_CAPITAL)
        growth = self.growth(series.days, capital)
        if growth.reason:
            return _refused(growth.reason)
        fund = fund_after_tax(growth.fund, series.days[0], series.days[-1], self.terms)
        cash = growth.cash - self.terms.cash_tax * max(growth.cash, 0.0)
        per = lambda rs: round(rs / capital_days, 8)  # noqa: E731
        verdict = None if ai_cost is None else book > fund
        return {
            "capital_days_rs": rupees(capital_days), "book_after_tax_rs": rupees(book),
            "fund_after_tax_rs": rupees(fund), "cash_after_tax_rs": rupees(cash), "book_per_rupee_day": per(book),
            "fund_per_rupee_day": per(fund), "cash_per_rupee_day": per(cash), "beats_index_after_tax": verdict,
            "beats_cash_after_tax": None if ai_cost is None else book > cash,
            "reason": BEFORE_AI if ai_cost is None else "",
        }  # fmt: skip

    def _view_b(self, series, capital, book: float, ai_cost: float | None, unrecorded) -> dict:
        if unrecorded:
            return _refused(NO_CAPITAL_RECORDED.format(ids=", ".join(unrecorded)))
        if not series.days:
            return _refused("no session")
        account = self.terms.account_rs
        idle = self.growth(series.days, [account - c for c in capital])
        whole = self.growth(series.days, [account] * len(capital))
        if idle.reason or whole.reason:
            return _refused(idle.reason or whole.reason)
        after_cash = lambda gain: gain - self.terms.cash_tax * max(gain, 0.0)  # noqa: E731
        fund = fund_after_tax(whole.fund, series.days[0], series.days[-1], self.terms)
        book_whole, cash = book + after_cash(idle.cash), after_cash(whole.cash)
        known = ai_cost is not None
        return {
            "account_rs": rupees(account), "book_with_idle_cash_rs": rupees(book_whole), "fund_rs": rupees(fund),
            "cash_rs": rupees(cash), "beats_index_after_tax": book_whole > fund if known else None,
            "beats_cash_after_tax": book_whole > cash if known else None, "reason": "" if known else BEFORE_AI,
        }  # fmt: skip


def _refused(reason: str) -> dict:
    return {"beats_index_after_tax": None, "beats_cash_after_tax": None, "reason": reason}
