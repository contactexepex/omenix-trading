"""A group of trades as daily pairs (story S2, S1's `primary_metric`): each session's net account change (the trades'
value changes, minus operating costs booked that day) and its risk at stake (the maximum loss at entry of every trade
held at the day's close). Net per unit of risk is the ratio of their means over the same days, so total net / risk-days:
it stays defined on days with no position and weights each day by the risk actually taken."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date

from .book_trades import ScoredTrade
from .daily_values import daily_changes


def rupees(value: float | None) -> float | None:
    """Rupees to the paisa, for every figure the scoreboards print."""
    return None if value is None else float(round(value, 2))


@dataclass(frozen=True)
class DailySeries:
    days: tuple[date, ...]
    net: tuple[float, ...]
    risk: tuple[float, ...]

    @property
    def total_net(self) -> float:
        return sum(self.net)

    @property
    def risk_days(self) -> float:
        return sum(self.risk)

    @property
    def net_per_risk(self) -> float | None:
        return self.total_net / self.risk_days if self.risk_days > 0 else None


def held_at_close(trade: ScoredTrade, day: date) -> bool:
    """Open at the day's close: entered on or before it and not closed by its end (an entry unwound the same day is
    never held, so it adds its cost and no risk)."""
    return trade.opened_on <= day and (trade.closed_on is None or day < trade.closed_on)


def daily_series(trades: Sequence[ScoredTrade], costs: Mapping[date, float], sessions: Sequence[date]) -> DailySeries:
    """The pairs over `sessions` (every session of the period, positions or not). A trade without a recorded maximum
    loss adds its money and no risk; the report lists it."""
    changes = [daily_changes(t.days) for t in trades]
    net, risk = [], []
    for day in sessions:
        net.append(sum(c.get(day, 0.0) for c in changes) - costs.get(day, 0.0))
        risk.append(sum(t.entry.max_loss for t in trades if t.entry and held_at_close(t, day)))
    return DailySeries(tuple(sessions), tuple(net), tuple(risk))


def costs_by_session(monthly: Mapping[str, float], sessions: Sequence[date]) -> dict[date, float]:
    """Each month's operating costs on its last session in the period (C1 dates costs by month only). A month with no
    session in the period books nothing here; the report shows the monthly table beside."""
    last: dict[str, date] = {}
    for day in sessions:
        last[day.strftime("%Y-%m")] = day
    return {last[month]: amount for month, amount in monthly.items() if month in last}
