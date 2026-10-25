"""V2's and V3's intraday versions (PROTOCOL_v4.md section 1.1, wording W7; story G7b completion, part f): the sum of
A16's live intraday `RV_s` over the horizon `d+1..d+h`, a separate reported series beside the close-proxy one, never
pooled with it and never a family member. A void session voids the day; a session without its row leaves it
unresolved. The one place for the rule: G8 imports it, as it imports `series.py`."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date

from ..constants import V2_RV_5S, V3_RV_20S
from .implied import HorizonRv

INTRADAY_SUFFIX = "/intraday"
INTRADAY_SERIES = {f"{q}{INTRADAY_SUFFIX}": q for q in (V2_RV_5S, V3_RV_20S)}  # series key -> its question
# Wording W3 (owner, 24 Oct 2026: "both"): V1 and the intraday series carry two premium-adjusted yardsticks, B fitted
# on the close proxy and A on the intraday measure, each its own labelled row, never pooled.
RATIO_CLOSE_PROXY, RATIO_INTRADAY = "close_proxy", "intraday"
# Wording W8 (owner, 24 Oct 2026: "W8 - yes"): yardstick A's ratio window takes A16b's candle back-fill where A16 has
# no live row, counted as `backfill_window` in the stored ratio; never a forecast input, outcome or base rate.


def question_of(key: str) -> str:
    """The protocol question whose forecasts, baseline, loss, block and horizon a report key uses."""
    return INTRADAY_SERIES.get(key, key)


def intraday_horizon_sum(
    intraday: Mapping[date, float | None], ahead: Sequence[date]
) -> tuple[float | None, bool] | None:
    """`(sum, void)` over the horizon's sessions, `(None, True)` when any is void, None while a session has no row
    (unresolved). `intraday`: A16's live rows by session (None for a void one)."""
    if any(d not in intraday for d in ahead):
        return None
    values = [intraday[d] for d in ahead]
    return (None, True) if any(v is None for v in values) else (sum(values), False)


def intraday_horizon_rv(
    rv: Mapping[date, float | None], sessions: Sequence[date], horizon: int
) -> dict[date, HorizonRv]:
    """Yardstick A's window points: for each scored session t whose next `horizon` sessions all have a non-void row,
    `RV_h(t)` (`implied.HorizonRv`) resolved at `t+h`; a void or missing session leaves t out."""
    found = {}
    for i, t in enumerate(sessions[: len(sessions) - horizon]):
        ahead = sessions[i + 1 : i + 1 + horizon]
        summed = intraday_horizon_sum(rv, ahead)
        if summed is not None and not summed[1]:
            found[t] = HorizonRv(summed[0], ahead[-1])
    return found


def backfill_window_points(sessions: Sequence[date], horizon: int, backfilled: set[date]) -> set[date]:
    """The window points t whose horizon `t+1..t+h` holds a back-filled session (W8's `backfill_window` label)."""
    return {t for i, t in enumerate(sessions) if backfilled.intersection(sessions[i + 1 : i + 1 + horizon])}
