"""Question 5's threshold per input mode (G1 protocol v3 section 4; response 69 item 7; judge 64): history
(`close_proxy`) is resolved against the panel's close-proxy IV30 of the day, as v1 defines; live (`live_1500_proxy`)
against the 15:00 IV30 locked in that day's receipt-verified pack, never a value computed later. This module is the one
place that decides it, so protocol v3 freezes it (with `resolution.py` and `score_sources.py`) instead of G4's shared
composition root.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from datetime import date

from ..forecast.closes_source import OfficialCloses
from ..forecast.iv30 import AtmIv30
from ..research_data.calendar import SessionCalendar
from .resolution import OfficialOutcomes
from .score_inputs import CLOSE_PROXY, LIVE

INTERPOLATED, FLAGGED = "interpolated", "flagged"


def pack_iv30(pack: bytes) -> AtmIv30 | None:
    """The pack's 15:00 IV30 (protocol v2 section 2), which live question 5 is scored against (response 69, item 7)."""
    iv30 = json.loads(pack).get("iv30")
    if not iv30 or iv30.get("status") not in (INTERPOLATED, FLAGGED):
        return None
    expiries = tuple(date.fromisoformat(e) for e in iv30.get("expiries", ()))
    return AtmIv30(float(iv30["points"]), iv30["status"] == FLAGGED, expiries)


def mode_resolvers(
    closes: OfficialCloses,
    calendar: SessionCalendar,
    as_of: date,
    panel_iv30: Callable[[date], tuple[bool, AtmIv30 | None]],
    pack_iv30_by_day: Mapping[date, AtmIv30 | None],
    horizon_day: Callable[[date, int], date | None],
) -> dict[str, OfficialOutcomes]:
    """One outcome resolver per input mode; they differ only in question 5's IV30."""
    return {
        CLOSE_PROXY: OfficialOutcomes(closes, calendar, as_of, panel_iv30, horizon_day),
        LIVE: OfficialOutcomes(closes, calendar, as_of, lambda day: (True, pack_iv30_by_day.get(day)), horizon_day),
    }
