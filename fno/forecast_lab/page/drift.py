"""The drift banner's rule (story FL1-1c v2; thresholds from the orchestrator's brief, 21 Oct 2026). Over the last
`ROLLING` (20) sessions, a method with bands is out of range when its 90% band held under 80% of closes, or its 50%
band held under 35% or over 65%. Data is a problem when a method has fewer than 20 scored forecasts there, or when
the latest scored session is older than the previous session. False alarms (some evidence: exact binomial, a
well-calibrated method, 20 independent sessions): about 4% for the 90% rule and about 12% for the 50% rule, per
method and horizon; with five methods, two horizons and two indices, a red banner on a calm week is likely. So the
banner names the method and the number, and one red line is a reason to look, not proof of a fault."""

from __future__ import annotations

from datetime import date

from .history import ROLLING
from .model import MethodRecord, Problem

MIN_90 = 0.80
BAND_50 = (0.35, 0.65)
HORIZON_WORDS = {"N1": "next session", "N3": "3 sessions"}
GAP = (
    "no forecast was issued for {expected}, so it has no score "
    "(a gap in the record, not a late score; newest scored close {latest})"
)


def _trailing(record: MethodRecord):
    return next((w for w in record.windows if w.sessions >= ROLLING), None)


def method_problems(underlying: str, horizon: str, record: MethodRecord, history_20: list[date]) -> list[Problem]:
    """Problems of one method over the trailing 20 sessions (`history_20`); a point forecast has no band to check."""
    group = f"{underlying} {HORIZON_WORDS.get(horizon, horizon)}"
    scored = [c for c in record.cells if c.day in set(history_20) and c.inside_90 is not None]
    if all(c.inside_90 is None for c in record.cells):
        return []
    if len(scored) < ROLLING:
        return [
            Problem(group, record.method, f"only {len(scored)} of the last {ROLLING} sessions scored (missing data)")
        ]
    in_90 = sum(c.inside_90 for c in scored) / ROLLING
    in_50 = sum(bool(c.inside_50) for c in scored) / ROLLING
    problems = []
    if in_90 < MIN_90:
        problems.append(
            Problem(
                group, record.method, f"90% band held {in_90:.0%} of the last {ROLLING} closes (normal: 80% or more)"
            )
        )
    if not BAND_50[0] <= in_50 <= BAND_50[1]:
        problems.append(
            Problem(
                group, record.method, f"50% band held {in_50:.0%} of the last {ROLLING} closes (normal: 35% to 65%)"
            )
        )
    return problems


def stale(underlying: str, latest: date | None, expected: date, issued: bool = True) -> list[Problem]:
    """The newest scored session must be `expected` (the edition's newest scorable session). When no forecast was
    issued for it, nothing can score it: that is a gap in the record, said as such, not a late score (FL1-1e)."""
    if latest is not None and latest >= expected:
        return []
    if not issued:
        return [Problem(underlying, "data", GAP.format(expected=expected, latest=latest or "none"))]
    return [Problem(underlying, "data", f"newest scored close is {latest or 'none'}, expected {expected} (stale)")]
