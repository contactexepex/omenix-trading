"""Forward diagnostic of the premium ratio's EOD proxy (PROTOCOL_v4.md section 3.1; ChatGPT review 99, finding 5).

Each live day pairs the 15:00 pack's IV30 with the same day's end-of-day proxy IV30. The report gives the paired count,
the median ratio 15:00 / EOD over all days and over the latest 20, and their difference (the drift). Descriptive only:
it never feeds the ratio or a baseline, and no result is ever read as proving the two are equivalent.
"""

from __future__ import annotations

import statistics
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

RECENT_DAYS = 20


@dataclass(frozen=True)
class ProxyDrift:
    pairs: int
    median_ratio: float | None  # 15:00 IV30 / EOD IV30, every paired day
    recent_median_ratio: float | None  # the latest 20 paired days
    drift: float | None  # recent minus all; reported, never acted on


def proxy_drift(days: Sequence[tuple[date, float | None, float | None]]) -> ProxyDrift:
    """`days`: (day, 15:00 IV30, EOD IV30); a day missing either value is not paired."""
    ratios = [live / eod for _, live, eod in sorted(days) if live and eod]
    if not ratios:
        return ProxyDrift(0, None, None, None)
    overall, recent = statistics.median(ratios), statistics.median(ratios[-RECENT_DAYS:])
    return ProxyDrift(len(ratios), overall, recent, recent - overall)
