"""One section of scoreboard B (story S2, design 12.5): every number the design lists for a group of a book's trades
over a period. Raw account net is the daily series' total (trades' realised and marked changes minus operating costs);
net also takes the allocated AI cost (F8, "allocated, not a bill") when it is known, and says so when it is not."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import date

from ..costs import CHARGE_NAMES
from .book_trades import ScoredTrade
from .series import DailySeries, held_at_close, rupees
from .t_check import DISAGREES, t_check
from .trade_measures import drawdown, trade_measures
from .uncertainty import FIGURES_STATUS, Uncertainty

AI_NOT_AVAILABLE = "not available: F8 (AI cost allocation) not built"
MARGIN_AT_ENTRY = "capital tied at entry (broker margin + premium paid) x sessions held (not re-margined daily)"


def _money(trades: Sequence[ScoredTrade]) -> dict:
    lines = [t.line for t in trades if t.line]
    charges = {name: sum(line.charges[name] for line in lines) for name in CHARGE_NAMES}
    pads = sum(line.pads for line in lines)
    return {
        "closed_trades": len(lines), "gross_rs": rupees(sum(line.gross for line in lines)), "pads_rs": rupees(pads),
        "charges_rs": {name: rupees(value) for name, value in charges.items()},
        "execution_costs_rs": rupees(pads + sum(charges.values())),
        "closed_net_rs": rupees(sum(line.net for line in lines)),
    }  # fmt: skip


def _risk(trades: Sequence[ScoredTrade], series: DailySeries) -> dict:
    held = {t.trade_id: sum(held_at_close(t, d) for d in series.days) for t in trades}
    margins = [t.entry.capital_tied * held[t.trade_id] for t in trades if t.entry and t.entry.capital_tied]
    reserves = [t.entry.stress_reserve * held[t.trade_id] for t in trades if t.entry and t.entry.stress_reserve]
    usage = [t.entry.stress_usage for t in trades if t.entry and t.entry.stress_usage is not None]
    return {
        "max_loss_at_entry_rs": rupees(sum(t.entry.max_loss for t in trades if t.entry)),
        "risk_days_rs": rupees(series.risk_days),
        "mean_daily_risk_rs": rupees(series.risk_days / len(series.days)) if series.days else None,
        "net_per_unit_of_risk": None if series.net_per_risk is None else round(series.net_per_risk, 6),
        "margin_days_rs": rupees(sum(margins)), "margin_days_method": MARGIN_AT_ENTRY,
        "stress_reserve_days_rs": rupees(sum(reserves)),
        "stress_usage_at_entry_max": round(max(usage), 6) if usage else None,
        "no_max_loss": sorted(t.trade_id for t in trades if t.entry is None),
        "no_capital": sorted(t.trade_id for t in trades if t.entry and t.entry.capital_tied is None),
    }  # fmt: skip


def _valuation(trades: Sequence[ScoredTrade]) -> dict:
    stale = sorted({(d.day.isoformat(), c) for t in trades for d in t.days for c in d.stale})
    unvalued = sorted({(t.trade_id, d.day.isoformat()) for t in trades for d in t.days if d.value is None})
    return {"stale_marks": [list(s) for s in stale], "unvalued_days": [list(u) for u in unvalued]}


def section(
    trades: Sequence[ScoredTrade], series: DailySeries, operating_costs: float, ai_cost: float | None,
    uncertainty: Uncertainty | None, first: date | None, last: date | None, brake_rs: float | None = None,
    against: Callable[[DailySeries, list[float], list[str]], dict] | None = None,
) -> dict:  # fmt: skip
    raw = series.total_net
    return {
        "period": {"first": first.isoformat() if first else None, "last": last.isoformat() if last else None,
                   "sessions": len(series.days)},
        "trades": {"positions": sum(t.completed and t.line is not None for t in trades),
                   "open": sum(t.closed_on is None for t in trades),
                   "unwound_entries": sum(not t.completed for t in trades), "ids": [t.trade_id for t in trades]},
        **_money(trades),
        "operating_costs_rs": rupees(operating_costs),
        "ai_cost_allocated_rs": rupees(ai_cost) if ai_cost is not None else AI_NOT_AVAILABLE,
        "raw_account_net_rs": rupees(raw),
        "net_rs": rupees(raw - ai_cost) if ai_cost is not None else None,
        "risk": _risk(trades, series),
        "uncertainty": None if uncertainty is None else _judged(uncertainty, series),
        "measures": _measures(trades, series, brake_rs),
        **_against(against, trades, series),
        "valuation": _valuation(trades),
    }  # fmt: skip


def _judged(uncertainty: Uncertainty, series: DailySeries) -> dict:
    """S1's criterion, with the t-check beside it: a printed warning, never a pass condition (story S6)."""
    check = t_check(series, uncertainty.lower_bound)
    warning = check["agrees_with_bootstrap"] is False
    return {
        "lower_bound": None if uncertainty.lower_bound is None else round(uncertainty.lower_bound, 6),
        "sample_met": uncertainty.sample_met, "claim_allowed": uncertainty.claim_allowed,
        "reason": f"{uncertainty.reason}; {DISAGREES}" if warning else uncertainty.reason,
        "figures": FIGURES_STATUS, "t_check": check,
    }  # fmt: skip


def _measures(trades: Sequence[ScoredTrade], series: DailySeries, brake_rs: float | None) -> dict:
    nets = [t.line.net for t in trades if t.completed and t.line is not None]
    return {**trade_measures(nets, sum(t.closed_on is None for t in trades)), **drawdown(series, brake_rs)}


def capital_path(trades: Sequence[ScoredTrade], series: DailySeries) -> list[float]:
    """Capital tied at each session's close: every held trade's capital at entry (S2's margin-days basis)."""
    return [sum(t.entry.capital_tied for t in trades if t.entry and t.entry.capital_tied and held_at_close(t, day))
            for day in series.days]  # fmt: skip


def _unrecorded(trades: Sequence[ScoredTrade]) -> list[str]:
    return sorted(t.trade_id for t in trades if t.entry and t.entry.capital_tied is None)


def _against(against, trades: Sequence[ScoredTrade], series: DailySeries) -> dict:
    return {} if against is None else {"do_nothing": against(series, capital_path(trades, series), _unrecorded(trades))}
