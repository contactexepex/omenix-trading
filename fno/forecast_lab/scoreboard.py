"""The 15:45 report's running scoreboard and trust line (story FL1-1): G13b's live scores summed per forecaster,
horizon and method version (never pooled across versions), lowest mean quantile score first, with each band's hit rate
beside the rate it should have (50% inside the 25-75 band, 90% inside 5-95). Counts are in trading days: one day's
forecasts are one outcome."""

from __future__ import annotations

from collections import defaultdict
from datetime import date

from .constants import CALIBRATION_DAYS, EDGE_WINDOW, TRUST
from .ranges import RangeScore, RangeSource


def _rate(flags: list[bool | None]) -> str:
    known = [f for f in flags if f is not None]
    return "n/a" if not known else f"{100 * sum(known) / len(known):.0f}%"


def scoreboard_lines(scores: list[RangeScore]) -> list[str]:
    groups: dict[tuple[str, str, str], list[RangeScore]] = defaultdict(list)
    for score in scores:
        groups[(score.horizon, score.forecaster, score.method)].append(score)
    versions = defaultdict(set)
    for horizon, forecaster, method in groups:
        versions[(horizon, forecaster)].add(method)
    if not groups:
        return ["Scoreboard: no live score yet"]
    rows = sorted(groups.items(), key=lambda item: (item[0][0], _mean(item[1])))
    lines = ["Scoreboard (live scores; lower quantile score is better; bands should hold 50% and 90%):"]
    for (horizon, forecaster, method), group in rows:
        tag = f" [method {method[:8]}]" if len(versions[(horizon, forecaster)]) > 1 else ""
        briers = [s.brier_up for s in group if s.brier_up is not None]
        brier = "n/a" if not briers else f"{sum(briers) / len(briers):.3f}"
        lines.append(
            f"  {horizon} {forecaster}{tag}: {len({s.target_day for s in group})} day(s), mean quantile score "
            f"{_mean(group):.2f}, 25-75 {_rate([s.inside_25_75 for s in group])}, "
            f"5-95 {_rate([s.inside_05_95 for s in group])}, P(up) Brier {brier}"
        )
    return lines


def _mean(group: list[RangeScore]) -> float:
    return sum(s.quantile_score for s in group) / len(group)


def trust_line(forecasts: RangeSource, underlyings: tuple[str, ...], day: date) -> str:
    days = set().union(*(forecasts.scored_days(u, day) for u in underlyings))
    return TRUST.format(days=len(days), needed=CALIBRATION_DAYS, edge=EDGE_WINDOW)
