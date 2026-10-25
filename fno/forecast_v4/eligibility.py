"""Which baseline is a date's primary comparison (PROTOCOL_v4.md section 3.2).

A baseline is eligible on a date only when it could be computed from inputs first seen before that date's 15:00 cutoff
with its full minimum history (section 3.2's table). V1's primary is HAR on intraday RV from the first date that model
is eligible, HAR on daily RV before; the switch is one way. Every other question has one primary. When the primary is
not eligible the pair is missing (counted), never filled by another baseline.

The premium-adjusted baseline's ratio window (section 3.1) is the one history that does not exist live: live 15:00 IV30
starts on 13 Oct 2026. Its window points therefore use the labelled end-of-day proxy (`V4_IV30_EOD_PROXY`: G1 v1's
`PanelAtmIv30` on the A3 panel's first-archived chains), only from 1 Jan 2024 (UDiFF files, and outside G1's 2019-2023
holdout).
"""

from __future__ import annotations

from collections.abc import Iterable, Set
from datetime import date

from ..constants import V1_RV_1S, V4_BASELINE_HAR_DAILY, V4_BASELINE_HAR_INTRADAY
from .terms import PRIMARY_BASELINE

PREMIUM_WINDOW_START = date(2024, 1, 1)
PREMIUM_WINDOW_MAX, PREMIUM_WINDOW_MIN = 750, 500


def primary_baseline(question: str, eligible: Set[str], intraday_started: bool) -> str | None:
    """The baseline that date's pair uses, or None (the pair is missing). `intraday_started`: intraday HAR was eligible
    on some earlier date of this question, so daily HAR can no longer stand in."""
    if question == V1_RV_1S:
        if V4_BASELINE_HAR_INTRADAY in eligible:
            return V4_BASELINE_HAR_INTRADAY
        return None if intraday_started or V4_BASELINE_HAR_DAILY not in eligible else V4_BASELINE_HAR_DAILY
    declared = PRIMARY_BASELINE[question]
    return declared if declared in eligible else None


def premium_ratio_window(rows: Iterable[tuple[date, date]], refit_day: date) -> list[date] | None:
    """The ratio's window at a refit: `rows` are (day t, the day its RV_h(t) resolved) for days with an unflagged EOD
    IV30 and a resolved, non-void outcome. Kept: t on or after 1 Jan 2024 and resolved before `refit_day`; the most
    recent 750 of them. None (baseline not eligible) with fewer than 500."""
    kept = sorted(t for t, resolved in rows if t >= PREMIUM_WINDOW_START and resolved < refit_day)
    return kept[-PREMIUM_WINDOW_MAX:] if len(kept) >= PREMIUM_WINDOW_MIN else None
