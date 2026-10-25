"""The scorecard measures beside the headline (story S6 section 2; owner, 15 Oct 2026, rows "Scorecard: S1's headline
kept" and "Largest loss share of gains replaced"): net without the best trade, the profit factor, and the maximum
drawdown and worst day of the daily series. Descriptive, never the verdict. Trade nets are completed positions only;
the drawdown and worst day are marked daily, not the brake's closed equity."""

from __future__ import annotations

from collections.abc import Sequence

from .series import DailySeries, rupees

NO_LOSS, NO_TRADE, NO_DAY = "no losing trade", "no completed trade", "no session"
NO_LOSING_DAY = "no losing day yet"
MARKED = "marked daily, not the brake's closed equity"
BY_DECISION_DAY = "one-lot results on their decision day, no daily marks (scoreboard A)"


def trade_measures(nets: Sequence[float], open_trades: int) -> dict:
    """Net without the best trade and the profit factor (undefined, never infinite, with no losing trade)."""
    wins, losses = [n for n in nets if n > 0], [n for n in nets if n < 0]
    if not nets:
        return {"completed": 0, "open_left_out": open_trades, "net_without_best_rs": None, "profit_factor": None,
                "profit_factor_reason": NO_TRADE}  # fmt: skip
    factor = sum(wins) / -sum(losses) if losses else None
    return {
        "completed": len(nets), "open_left_out": open_trades,
        "net_without_best_rs": rupees(sum(nets) - max(nets)),
        "profit_factor": None if factor is None else round(factor, 6),
        "profit_factor_reason": "" if losses else NO_LOSS,
        "winners": len(wins), "losers": len(losses),
        "gains_rs": rupees(sum(wins)), "losses_rs": rupees(sum(losses)),
    }  # fmt: skip


def drawdown(series: DailySeries, brake_rs: float | None, label: str = MARKED) -> dict:
    """The deepest fall of the cumulative daily net below its running high (which starts at 0 before the first
    session) and the worst day, in rupees and, when a brake applies, as a share of it."""
    if not series.days:
        return {"label": label, "max_drawdown_rs": None, "worst_day_rs": None, "reason": NO_DAY}
    high = cumulative = deepest = 0.0
    peak_day, deepest_at = None, (None, None)
    for day, net in zip(series.days, series.net, strict=True):
        cumulative += net
        if cumulative > high:
            high, peak_day = cumulative, day
        if high - cumulative > deepest:
            deepest, deepest_at = high - cumulative, (peak_day, day)
    worst = min(range(len(series.days)), key=lambda i: (series.net[i], series.days[i]))
    share = lambda rs: None if not brake_rs else round(rs / brake_rs, 6)  # noqa: E731
    lost = series.net[worst] < 0  # a Rs 0.00 "worst day" misleads (orchestrator, 16 Oct): no worst day until a loss
    return {
        "label": label, "max_drawdown_rs": rupees(deepest), "max_drawdown_share_of_brake": share(deepest),
        "drawdown_from": deepest_at[0].isoformat() if deepest_at[0] else None,
        "drawdown_to": deepest_at[1].isoformat() if deepest_at[1] else None,
        "worst_day_rs": rupees(series.net[worst]) if lost else None,
        "worst_day": series.days[worst].isoformat() if lost else None,
        "worst_day_share_of_brake": share(-series.net[worst]) if lost else None,
        "worst_day_reason": "" if lost else NO_LOSING_DAY,
    }  # fmt: skip
