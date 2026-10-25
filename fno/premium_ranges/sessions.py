"""Session-first averaging and the verdict rule (story "Outcome and scores", judge 453 SF1). All contracts of one day
share one index move, so every figure is first averaged per session, then over sessions, and every interval is G4's
moving-block bootstrap over sessions (block 20, 10,000 resamples); rows are never treated as independent.

The verdict, per underlying, is read only at 60, 120 and 250 scored sessions, each on its first L sessions:
- coverage: *covers well* when the 90% coverage's interval lies inside [0.85, 0.95] and the 50% coverage's inside
  [0.40, 0.60]; *fails* when either interval lies wholly outside its band; else *not yet decided*;
- carry: *beats carry* when the paired rupee-QS difference (rule minus decay_only) has its interval below 0; *fails*
  when it lies wholly above 0; else *not yet decided*. Against no_change it is reported, never decided on."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from ..forecast.comparisons import MIN_PAIRED_DATES
from ..forecast_scoring.block_bootstrap import INTERVAL_PERCENTILES, resampled_means
from .constants import (
    BAND_50,
    BAND_90,
    BEATS_CARRY,
    COVERS_WELL,
    DECAY_ONLY,
    FAILS,
    LOOKS,
    METHODS,
    NO_CHANGE,
    NOT_YET,
    RULE,
)
from .scores import Scored

QS, RELATIVE, INSIDE_50, INSIDE_90 = range(4)
NEXT_LOOK, ALL_READ = "next look at {n} scored sessions", "all looks read"
SEEDS = {"inside_90": 0, "inside_50": 1, "minus_decay_only": 2, "minus_no_change": 3}  # G4's comparison index k


@dataclass(frozen=True)
class Session:
    day: str
    means: dict[str, tuple[float, float, float, float]]  # method -> mean QS, relative QS, inside 50%, inside 90%
    rows: int


def session_of(day: str, rows: Sequence[Scored]) -> Session | None:
    if not rows:
        return None
    means = {m: tuple(float(np.mean([r.by_method[m][i] for r in rows])) for i in range(4)) for m in METHODS}
    return Session(day, means, len(rows))


def interval(values: Sequence[float], k: int) -> list[float] | None:
    if len(values) < MIN_PAIRED_DATES:
        return None
    low, high = np.percentile(resampled_means(values, k), INTERVAL_PERCENTILES)
    return [round(float(low), 6), round(float(high), 6)]


def series(sessions: Sequence[Session]) -> dict[str, list[float]]:
    return {"inside_90": [s.means[RULE][INSIDE_90] for s in sessions],
            "inside_50": [s.means[RULE][INSIDE_50] for s in sessions],
            "minus_decay_only": [s.means[RULE][QS] - s.means[DECAY_ONLY][QS] for s in sessions],
            "minus_no_change": [s.means[RULE][QS] - s.means[NO_CHANGE][QS] for s in sessions]}  # fmt: skip


def summary(sessions: Sequence[Session]) -> dict:
    """Means over sessions per method, and the rule's coverage and paired differences with their intervals."""
    out = {"sessions": len(sessions), "rows": sum(s.rows for s in sessions),
           "methods": {m: dict(zip(("mean_qs_rs", "mean_relative_qs", "inside_50", "inside_90"),
                                   (round(float(np.mean([s.means[m][i] for s in sessions])), 6) for i in range(4)),
                                   strict=True)) for m in METHODS} if sessions else {}}  # fmt: skip
    for name, values in series(sessions).items():
        out[name] = {"mean": round(float(np.mean(values)), 6) if values else None,
                     "interval_95": interval(values, SEEDS[name])}  # fmt: skip
    return out


def _inside(found: list[float] | None, band: tuple[float, float]) -> bool:
    return found is not None and band[0] <= found[0] and found[1] <= band[1]


def _outside(found: list[float] | None, band: tuple[float, float]) -> bool:
    return found is not None and (found[1] < band[0] or found[0] > band[1])


def verdict(first: Sequence[Session]) -> dict:
    """The verdict on exactly these sessions (a look's first L)."""
    s = summary(first)
    i90, i50, carry = s["inside_90"]["interval_95"], s["inside_50"]["interval_95"], s["minus_decay_only"]["interval_95"]
    coverage = (COVERS_WELL if _inside(i90, BAND_90) and _inside(i50, BAND_50)
                else FAILS if _outside(i90, BAND_90) or _outside(i50, BAND_50) else NOT_YET)  # fmt: skip
    beats = BEATS_CARRY if carry and carry[1] < 0 else FAILS if carry and carry[0] > 0 else NOT_YET
    return {"sessions": len(first), "coverage": coverage, "carry": beats, "inside_90_interval": i90,
            "inside_50_interval": i50, "minus_decay_only_interval": carry}  # fmt: skip


def looks(sessions: Sequence[Session]) -> dict:
    """Every reached look's verdict on its first L sessions, and the next look."""
    reached = [look for look in LOOKS if len(sessions) >= look]
    following = next((look for look in LOOKS if len(sessions) < look), None)
    status = NEXT_LOOK.format(n=following) if following else ALL_READ
    return {"verdicts": {str(look): verdict(sessions[:look]) for look in reached}, "status": status}
