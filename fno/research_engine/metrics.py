"""The protocol's metrics for one policy over one period (story B3, protocol sections 7 and 9). Per-opportunity
statistics count every opportunity (no trade and every non-traded status are Rs 0); traded-only statistics are kept
separate. A cycle's P&L belongs to its exit day (calendar year and Indian financial year, April-March). Nothing is
rounded here."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from datetime import date

from .opportunities import Action, Opportunity, pnl_series

FY_START_MONTH = 4  # Indian financial year: April to March


def longest_losing_run(pnl: Sequence[float]) -> int:
    """The most consecutive opportunities with a loss (a zero ends a run)."""
    best = run = 0
    for value in pnl:
        run = run + 1 if value < 0 else 0
        best = max(best, run)
    return best


def max_drawdown(pnl: Sequence[float]) -> float:
    """The largest fall of cumulative P&L from its previous peak (the start, 0, counts as a peak), as a positive
    number of rupees."""
    peak = cumulative = worst = 0.0
    for value in pnl:
        cumulative += value
        peak = max(peak, cumulative)
        worst = max(worst, peak - cumulative)
    return worst


def financial_year(day: date) -> str:
    first = day.year if day.month >= FY_START_MONTH else day.year - 1
    return f"{first}-{str(first + 1)[2:]}"


def yearly(opportunities: Sequence[Opportunity], pnl: Sequence[float], key) -> dict[str, float]:
    totals: dict[str, float] = {}
    for opportunity, value in zip(opportunities, pnl, strict=True):
        label = key(opportunity.cycle.exit_day)
        totals[label] = totals.get(label, 0.0) + value
    return dict(sorted(totals.items()))


def tax_by_financial_year(by_year: dict[str, float], rate: float) -> dict[str, dict[str, float]]:
    """Protocol section 9 (assumed, reported only): rate x max(0, the year's net); losses offset within the year; no
    carry-forward."""
    return {fy: {"net": net, "tax": rate * max(0.0, net)} for fy, net in by_year.items()}


def policy_summary(opportunities: Sequence[Opportunity], chosen: Sequence[Action], tax_rate: float) -> dict:
    pnl = pnl_series(opportunities, chosen)
    traded = [v for o, a, v in zip(opportunities, chosen, pnl, strict=True) if o.traded(a)]
    total = sum(pnl)
    by_year = yearly(opportunities, pnl, lambda day: str(day.year))
    by_fy = yearly(opportunities, pnl, financial_year)
    tax = tax_by_financial_year(by_fy, tax_rate)
    losses = [o.result(a).max_loss for o, a in zip(opportunities, chosen, strict=True) if o.traded(a)]
    impossible = [v for o, a, v in zip(opportunities, chosen, pnl, strict=True) if o.exit_outside_payoff(a)]
    return {
        "opportunities": len(pnl),
        "total_net": total,
        "mean_net": total / len(pnl) if pnl else 0.0,
        "traded": len(traded),
        "traded_total_net": sum(traded),
        "traded_mean_net": sum(traded) / len(traded) if traded else None,
        "win_rate_traded": sum(v > 0 for v in traded) / len(traded) if traded else None,
        "worst_opportunity": min(pnl) if pnl else None,
        "longest_losing_run": longest_losing_run(pnl),
        "max_drawdown": max_drawdown(pnl),
        "net_by_year": by_year,
        "best_year_share": max(by_year.values()) / total if by_year and total > 0 else None,
        "status_counts": dict(sorted(Counter(o.status(a) for o, a in zip(opportunities, chosen, strict=True)).items())),
        "tax_by_financial_year": tax,
        "tax_total": sum(year["tax"] for year in tax.values()),
        "no_settlement_total_net": sum(o.no_settlement_pnl(a) for o, a in zip(opportunities, chosen, strict=True)),
        "largest_modelled_max_loss": max(losses) if losses else None,
        "exits_outside_payoff": len(impossible),  # report only: how much of the result rests on impossible closes
        "exits_outside_payoff_net": sum(impossible),
    }
